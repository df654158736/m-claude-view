"""Tool registry for managing available tools."""
from typing import Dict, List

from src.infrastructure.tools.base import Tool


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        """Get a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        return self._tools[name]

    def execute(self, name: str, arguments: dict) -> str:
        """Execute a tool by name with given arguments."""
        tool = self.get_tool(name)
        return tool.execute(**arguments)

    def get_tool_schemas(self) -> List[dict]:
        """Get tool schemas for LLM."""
        schemas = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        return schemas
