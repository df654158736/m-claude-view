"""Tool registry for managing available tools."""
from typing import Dict, List

from src.infrastructure.tools.base import Tool


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        return self._tools[name]

    def execute(self, name: str, arguments: dict) -> str:
        tool = self.get_tool(name)
        parsed = tool.parse_args(arguments)
        return tool.execute(parsed)

    def summary(self) -> list[dict]:
        """Return a summary of all registered tools for startup reporting."""
        items = []
        for tool in self._tools.values():
            params = tool.parameters.get("properties", {})
            param_names = list(params.keys())
            required = tool.parameters.get("required", [])
            items.append({
                "name": tool.name,
                "type": type(tool).__name__,
                "description": tool.description,
                "params": param_names,
                "required": required,
            })
        return items

    def get_tool_schemas(self) -> List[dict]:
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
