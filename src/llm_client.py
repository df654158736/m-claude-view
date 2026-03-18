"""LLM Client for interacting with DashScope API."""
import json
from dataclasses import dataclass
from typing import Optional, List
from openai import OpenAI


@dataclass
class ToolCall:
    """Represents a tool call from the model."""
    id: str
    name: str
    arguments: dict


class LLMClient:
    """Client for LLM API interactions."""

    def __init__(self, config):
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.temperature = config.temperature
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def chat(self, messages: list, tools: Optional[List] = None):
        """Send a chat request to the LLM."""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }
        if tools:
            params["tools"] = tools

        response = self.client.chat.completions.create(**params)
        return response.choices[0]

    @staticmethod
    def parse_response(response) -> tuple[Optional[str], List[ToolCall]]:
        """Parse LLM response to extract content or tool calls."""
        message = response.message

        # Check for tool calls
        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                ))
            return None, tool_calls

        # Return content
        return message.content, []