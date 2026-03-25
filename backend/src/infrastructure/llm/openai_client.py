"""OpenAI-compatible client implementation."""
import json
from typing import List, Optional

from openai import OpenAI

from src.domain.agent.models import ToolCall


class LLMClient:
    """Client for LLM API interactions."""

    def __init__(self, config):
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.temperature = config.temperature
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(self, messages: list, tools: Optional[List] = None):
        """Send a chat request to the LLM."""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            params["tools"] = tools

        try:
            response = self.client.chat.completions.create(**params)
        except Exception as err:  # noqa: BLE001
            raise RuntimeError(f"LLM API 调用失败: {err}") from err

        return response.choices[0]

    @staticmethod
    def parse_response(response) -> tuple[Optional[str], List[ToolCall]]:
        """Parse LLM response to extract content or tool calls."""
        message = response.message

        if message.tool_calls:
            tool_calls = []
            for tool_call in message.tool_calls:
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {"error": "Failed to parse arguments"}

                tool_calls.append(
                    ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=arguments,
                    )
                )
            return None, tool_calls

        return message.content, []
