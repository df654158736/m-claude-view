"""ReAct Engine - Core reasoning and action loop."""
import logging
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
        self.max_iterations = config.max_iterations
        self.config = config

        # Message history
        self.messages = []

    def build_messages(self, user_task: str) -> list:
        """Build initial messages with system prompt."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_task}
        ]
        return messages

    def run(self, task: str) -> str:
        """Run the ReAct loop for a given task."""
        self.messages = self.build_messages(task)

        logger.info(f"Starting ReAct loop for task: {task[:50]}...")

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"--- Iteration {iteration}/{self.max_iterations} ---")

            # Get tool schemas
            tools = self.tool_registry.get_tool_schemas()

            # Call LLM
            response = self.llm_client.chat(self.messages, tools if tools else None)
            content, tool_calls = self.llm_client.parse_response(response)

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
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"
                    logger.error(result)

                # Add tool result to history
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })

        # Max iterations reached
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        return "任务未在最大迭代次数内完成"