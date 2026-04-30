"""ReAct engine domain service."""
import json
import logging
from typing import Any

from src.domain.agent.models import ToolCall
from src.domain.agent.packet_logger import PacketLogger
from src.domain.agent.prompt_templates import MCP_CATALOG_PROMPT, REACT_SYSTEM_PROMPT


logger = logging.getLogger("react_agent")


class ReActEngine:
    """ReAct 核心执行引擎。

    设计目标：
    1. 只负责"推理-行动-观察"的主流程编排，不关心 HTTP/CLI 入口细节。
    2. 将日志序列化、可读化输出、文件落盘等横切关注点委托给 PacketLogger。
    3. 保持会话级消息历史，支持多次 run() 共享上下文；需要时可 reset_session() 重置。
    """
    def __init__(self, llm_client, tool_registry, config):
        """注入依赖并初始化运行态。

        参数说明：
        - llm_client: 负责与模型通信，提供 chat / parse_response。
        - tool_registry: 工具注册表，提供工具 schema 与执行能力。
        - config: 全局配置对象，仅提取当前引擎关心的最小字段。
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_iterations = self._resolve_max_iterations(config)
        self.config = config
        self.packet_logger = PacketLogger.from_config(config=config, logger=logger)

        self.system_prompt = self._build_system_prompt()
        self.messages: list[dict[str, Any]] = [{"role": "system", "content": self.system_prompt}]

    def _build_system_prompt(self) -> str:
        prompt = REACT_SYSTEM_PROMPT
        try:
            catalog = self.tool_registry.get_mcp_catalog()
            if catalog and isinstance(catalog, list):
                lines = []
                for entry in catalog:
                    lines.append(f"- **{entry['name']}** ({entry['server']}): {entry['description'][:80]}")
                prompt += MCP_CATALOG_PROMPT.format(catalog="\n".join(lines))
        except (AttributeError, TypeError):
            pass
        return prompt

    def reset_session(self) -> None:
        """Clear accumulated conversation state and keep only system prompt."""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def build_messages(self, user_task: str) -> list[dict[str, str]]:
        """Build initial messages with system prompt."""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_task},
        ]

    def _log_packet(self, packet_type: str, iteration: int, **payload) -> None:
        """输出结构化观测包，用于前端时间线、问题回放与问题定位。

        注意：
        - 测试会 patch 当前模块 logger，因此这里每次同步 logger 引用。
        - 真实格式化/落盘逻辑由 PacketLogger 负责，Engine 不持有这些细节。
        """
        self.packet_logger.logger = logger
        self.packet_logger.log(packet_type, iteration, **payload)

    @staticmethod
    def _resolve_max_iterations(config) -> int:
        """解析最大迭代次数，兼容旧字段和新字段。"""
        max_iterations = getattr(config, "max_iterations", None)
        if not isinstance(max_iterations, int):
            llm_config = getattr(config, "llm", None)
            max_iterations = getattr(llm_config, "max_iterations", None)
        return max_iterations if isinstance(max_iterations, int) else 20

    def run(self, task: str) -> str:
        """执行一次完整的 ReAct 循环。

        主流程：
        1. 记录 user 输入并入会话历史；
        2. 每轮请求 LLM，解析 content/tool_calls；
        3. 无 tool_calls 则视为完成并返回；
        4. 有 tool_calls 则执行工具并回填 tool 消息，进入下一轮。
        """
        self.messages.append({"role": "user", "content": task})
        self._log_packet("user", 0, content=task)

        logger.info("Starting ReAct loop for task: %s...", task[:50])

        for iteration in range(1, self.max_iterations + 1):
            logger.info("--- Iteration %s/%s ---", iteration, self.max_iterations)

            content, tool_calls = self._request_llm(iteration)

            if content:
                self._log_packet("agent", iteration, content=content)
            if tool_calls:
                self._log_packet(
                    "agent",
                    iteration,
                    tool_calls=[
                        {
                            "id": tc.id,
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                        for tc in tool_calls
                    ],
                )

            self._append_assistant_message(content, tool_calls)

            if not tool_calls:
                logger.info("Task completed in %s iterations", iteration)
                return content or "No response"

            self._execute_tool_calls(iteration, tool_calls)

        logger.warning("Max iterations (%s) reached", self.max_iterations)
        return "任务未在最大迭代次数内完成"

    def _request_llm(self, iteration: int) -> tuple[str | None, list[ToolCall]]:
        """向模型发起请求并解析响应。

        该方法把"请求日志 + 模型调用 + 响应日志"封装在一起，
        让 run() 主循环保持线性可读。
        """
        tools = self.tool_registry.get_tool_schemas()
        self._log_packet(
            "llm_request",
            iteration,
            direction="outbound",
            messages=self.messages,
            tools=tools if tools else [],
        )
        response = self.llm_client.chat(self.messages, tools if tools else None)
        content, tool_calls = self.llm_client.parse_response(response)
        self._log_packet(
            "llm_response",
            iteration,
            direction="inbound",
            content=content,
            tool_calls=[
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                }
                for tc in tool_calls
            ],
        )
        return content, tool_calls

    def _append_assistant_message(self, content: str | None, tool_calls: list[ToolCall]) -> None:
        """将 assistant 回合写入会话历史。

        规则：
        - 有自然语言内容时写入 content；
        - 有工具调用时写入 OpenAI function-call 兼容结构；
        - 二者可并存，保证后续轮次上下文完整。
        """
        assistant_msg: dict[str, Any] = {"role": "assistant"}
        if content:
            assistant_msg["content"] = content
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in tool_calls
            ]
        self.messages.append(assistant_msg)

    def _execute_tool_calls(self, iteration: int, tool_calls: list[ToolCall]) -> None:
        """执行模型请求的工具，并把结果写回会话历史。

        失败策略：
        - 单个工具失败不会中断整轮流程；
        - 错误会被包装成文本结果返回给模型，让模型可自行修正下一步计划。
        """
        for tc in tool_calls:
            logger.info("Executing tool: %s with args: %s", tc.name, tc.arguments)
            try:
                result = self.tool_registry.execute(tc.name, tc.arguments)
                logger.info("Tool result: %s...", str(result)[:200])
                self._log_packet(
                    "tool",
                    iteration,
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result=result,
                )
            except Exception as err:  # noqa: BLE001
                result = f"Error executing tool: {str(err)}"
                logger.error(result)
                self._log_packet(
                    "tool",
                    iteration,
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result=result,
                )

            self.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
