"""ReAct Engine - Core reasoning and action loop."""
import json
import logging
from pathlib import Path
from typing import Optional
from src.llm_client import LLMClient, ToolCall
from src.tools.registry import ToolRegistry


logger = logging.getLogger("react_agent")


class ReActEngine:
    """ReAct (Reasoning + Acting) engine for agent execution."""

    SYSTEM_PROMPT = """你是一个 ReAct Agent。

## 工作流程
1. 思考当前任务状态
2. 如需执行操作，使用工具
3. 根据工具返回结果决定下一步
4. 完成任务后返回最终结果

## 规则
- 仔细分析工具返回的结果
- 如果结果不理想，反思原因并重试
- 只在确实完成目标后返回最终答案
- 如果需要执行shell命令，使用 bash 工具
"""

    def __init__(self, llm_client: LLMClient, tool_registry: ToolRegistry, config):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        display_config = getattr(config, "display", None)
        max_iterations = getattr(config, "max_iterations", None)
        if not isinstance(max_iterations, int):
            llm_config = getattr(config, "llm", None)
            max_iterations = getattr(llm_config, "max_iterations", None)
        self.max_iterations = max_iterations if isinstance(max_iterations, int) else 20
        self.config = config
        self.packet_log_mode = "json"
        self.color_logs = False
        self.json_pretty = False
        self.json_indent = 2
        self.packet_log_file: Optional[Path] = None
        display_mode = getattr(display_config, "packet_log_mode", None)
        config_mode = getattr(config, "packet_log_mode", None)
        display_color_logs = getattr(display_config, "color_logs", None)
        config_color_logs = getattr(config, "color_logs", None)
        display_json_pretty = getattr(display_config, "json_pretty", None)
        config_json_pretty = getattr(config, "json_pretty", None)
        display_json_indent = getattr(display_config, "json_indent", None)
        config_json_indent = getattr(config, "json_indent", None)
        display_packet_log_file = getattr(display_config, "packet_log_file", None)
        config_packet_log_file = getattr(config, "packet_log_file", None)
        if isinstance(display_mode, str) and display_mode:
            self.packet_log_mode = display_mode
        elif isinstance(config_mode, str) and config_mode:
            self.packet_log_mode = config_mode
        if isinstance(display_color_logs, bool):
            self.color_logs = display_color_logs
        elif isinstance(config_color_logs, bool):
            self.color_logs = config_color_logs
        if isinstance(display_json_pretty, bool):
            self.json_pretty = display_json_pretty
        elif isinstance(config_json_pretty, bool):
            self.json_pretty = config_json_pretty
        if isinstance(display_json_indent, int):
            self.json_indent = display_json_indent
        elif isinstance(config_json_indent, int):
            self.json_indent = config_json_indent
        packet_log_file = None
        if isinstance(display_packet_log_file, str) and display_packet_log_file.strip():
            packet_log_file = display_packet_log_file.strip()
        elif isinstance(config_packet_log_file, str) and config_packet_log_file.strip():
            packet_log_file = config_packet_log_file.strip()
        if packet_log_file:
            self.packet_log_file = Path(packet_log_file)

        # Session-level message history (kept across multiple run() calls).
        self.messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

    def build_messages(self, user_task: str) -> list:
        """Build initial messages with system prompt."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_task}
        ]
        return messages

    def _log_packet(self, packet_type: str, iteration: int, **payload) -> None:
        """Log a structured packet for tracing user/agent/tool flows."""
        packet = {"type": packet_type, "iteration": iteration, **payload}
        self._write_packet_file(packet)
        if self.packet_log_mode in ("json", "both"):
            logger.info(self._format_json_packet(packet))
        if self.packet_log_mode in ("readable", "both"):
            logger.info(self._format_readable_packet(packet_type, iteration, payload))

    def _format_json_packet(self, packet: dict) -> str:
        """Format packet as compact or pretty JSON."""
        if self.json_pretty:
            return json.dumps(packet, ensure_ascii=False, default=str, indent=self.json_indent)
        return json.dumps(packet, ensure_ascii=False, default=str, separators=(",", ":"))

    def _write_packet_file(self, packet: dict) -> None:
        """Append packet to JSONL file for machine-readable consumers."""
        if not self.packet_log_file:
            return
        try:
            self.packet_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.packet_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(packet, ensure_ascii=False, default=str, separators=(",", ":")))
                f.write("\n")
        except OSError as e:
            logger.warning(f"Failed to write packet log file: {e}")

    @staticmethod
    def _truncate(value, limit: int = 240) -> str:
        text = str(value)
        return text if len(text) <= limit else text[:limit] + "...(truncated)"

    def _format_readable_packet(self, packet_type: str, iteration: int, payload: dict) -> str:
        """Format readable packet lines for quick terminal inspection."""
        if packet_type == "user":
            line = f"[USER][iter={iteration}] {self._truncate(payload.get('content', ''))}"
            return self._with_color("user", line)
        if packet_type == "llm_request":
            msg_count = len(payload.get("messages", []))
            tool_count = len(payload.get("tools", []))
            line = f"[TO_LLM][iter={iteration}] messages={msg_count} tools={tool_count}"
            return self._with_color("llm_request", line)
        if packet_type == "llm_response":
            content = payload.get("content")
            tool_calls = payload.get("tool_calls", [])
            if tool_calls:
                names = ",".join(tc.get("name", "unknown") for tc in tool_calls)
                line = f"[FROM_LLM][iter={iteration}] tool_calls={len(tool_calls)} names={names}"
                return self._with_color("llm_response", line)
            line = f"[FROM_LLM][iter={iteration}] content={self._truncate(content)}"
            return self._with_color("llm_response", line)
        if packet_type == "tool":
            tool_name = payload.get("tool_name", "unknown")
            result = self._truncate(payload.get("result", ""))
            line = f"[TOOL][iter={iteration}][{tool_name}] result={result}"
            return self._with_color("tool", line)
        if packet_type == "agent":
            if "tool_calls" in payload:
                line = f"[AGENT][iter={iteration}] planned_tool_calls={len(payload['tool_calls'])}"
                return self._with_color("agent", line)
            line = f"[AGENT][iter={iteration}] content={self._truncate(payload.get('content', ''))}"
            return self._with_color("agent", line)
        line = f"[{packet_type.upper()}][iter={iteration}] {self._truncate(payload)}"
        return self._with_color(packet_type, line)

    def _with_color(self, packet_type: str, line: str) -> str:
        """Apply ANSI color styles to readable logs when enabled."""
        if not self.color_logs:
            return line
        color_map = {
            "user": "\033[36m",          # cyan
            "llm_request": "\033[34m",   # blue
            "llm_response": "\033[32m",  # green
            "agent": "\033[35m",         # magenta
            "tool": "\033[33m",          # yellow
        }
        color = color_map.get(packet_type, "\033[37m")
        return f"{color}{line}\033[0m"

    def run(self, task: str) -> str:
        """Run the ReAct loop for a given task."""
        self.messages.append({"role": "user", "content": task})
        self._log_packet("user", 0, content=task)

        logger.info(f"Starting ReAct loop for task: {task[:50]}...")

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"--- Iteration {iteration}/{self.max_iterations} ---")

            # Get tool schemas
            tools = self.tool_registry.get_tool_schemas()
            self._log_packet(
                "llm_request",
                iteration,
                direction="outbound",
                messages=self.messages,
                tools=tools if tools else []
            )

            # Call LLM
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
                        "arguments": tc.arguments
                    }
                    for tc in tool_calls
                ]
            )

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
                            "arguments": tc.arguments
                        }
                        for tc in tool_calls
                    ]
                )

            # Add assistant message to history
            assistant_msg = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": str(tc.arguments)
                        }
                    }
                    for tc in tool_calls
                ]
            self.messages.append(assistant_msg)

            # If no tool calls, return the final response
            if not tool_calls:
                logger.info(f"Task completed in {iteration} iterations")
                return content or "No response"

            # Execute tool calls
            for tc in tool_calls:
                logger.info(f"Executing tool: {tc.name} with args: {tc.arguments}")
                try:
                    result = self.tool_registry.execute(tc.name, tc.arguments)
                    logger.info(f"Tool result: {str(result)[:200]}...")
                    self._log_packet(
                        "tool",
                        iteration,
                        tool_name=tc.name,
                        arguments=tc.arguments,
                        result=result
                    )
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"
                    logger.error(result)
                    self._log_packet(
                        "tool",
                        iteration,
                        tool_name=tc.name,
                        arguments=tc.arguments,
                        result=result
                    )

                # Add tool result to history
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })

        # Max iterations reached
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        return "任务未在最大迭代次数内完成"
