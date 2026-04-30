"""Tool registry for managing available tools."""
from typing import Dict, List

from src.infrastructure.tools.base import Tool


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._mcp_catalog: Dict[str, dict] = {}
        self._deferred_mcp_tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        if name not in self._tools:
            if name in self._deferred_mcp_tools:
                self.activate_mcp_tools([name])
            else:
                raise ValueError(f"Tool not found: {name}")
        return self._tools[name]

    def execute(self, name: str, arguments: dict) -> str:
        tool = self.get_tool(name)
        parsed = tool.parse_args(arguments)
        return tool.execute(parsed)

    def register_mcp_catalog(self, server_name: str, sub_tools: list):
        """Store sub_tools in both _mcp_catalog and _deferred_mcp_tools."""
        for tool in sub_tools:
            self._mcp_catalog[tool.name] = {
                "name": tool.name,
                "mcp_tool_name": tool.name,
                "description": tool.description,
                "server": server_name,
            }
            self._deferred_mcp_tools[tool.name] = tool

    def get_mcp_catalog(self) -> list[dict]:
        """Return list of catalog entries for all deferred tools."""
        return list(self._mcp_catalog.values())

    def search_mcp_catalog(self, query: str) -> list[dict]:
        """Filter catalog by case-insensitive substring match in name or description."""
        q = query.lower()
        return [
            entry for entry in self._mcp_catalog.values()
            if q in entry["name"].lower() or q in entry["description"].lower()
        ]

    def activate_mcp_tools(self, names: list[str]) -> list[dict]:
        """Move matching tools from deferred to active, return their info."""
        activated = []
        for name in names:
            if name in self._deferred_mcp_tools:
                tool = self._deferred_mcp_tools.pop(name)
                self._mcp_catalog.pop(name, None)
                self._tools[name] = tool
                activated.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                })
            elif name in self._tools:
                tool = self._tools[name]
                activated.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                })
        return activated

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
        items.append({
            "deferred_mcp_tools_count": len(self._deferred_mcp_tools),
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
