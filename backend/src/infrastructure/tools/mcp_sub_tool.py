"""Proxy Tool that represents a single sub-tool from an MCP server."""
from __future__ import annotations

from typing import Any

from .base import Tool


class MCPSubTool(Tool):
    """A proxy for a single tool exposed by an MCP server.

    Unlike regular Tool subclasses, MCPSubTool does **not** declare a
    class-level ``name``, so it is never auto-registered via
    ``__init_subclass__``.  Instead, each instance receives its identity
    at construction time from the MCP tool descriptor and routes
    ``execute`` calls through the parent ``MCPServerTool``.
    """

    # No class-level name — prevents auto-registration.

    def __init__(self, server_name: str, mcp_tool_desc: dict, parent: Any) -> None:
        """Initialise from an MCP tool descriptor.

        Parameters
        ----------
        server_name:
            Logical name of the MCP server (e.g. ``"playwright"``).
        mcp_tool_desc:
            Dict with keys ``name``, ``description``, ``inputSchema``
            as returned by the MCP ``tools/list`` response.
        parent:
            The owning ``MCPServerTool`` instance whose ``call_tool``
            method will be used to actually invoke the sub-tool.
        """
        self.mcp_tool_name: str = mcp_tool_desc["name"]
        self.name = f"{server_name}__{self.mcp_tool_name}"
        self.description = mcp_tool_desc.get("description", "")
        self._input_schema: dict = dict(mcp_tool_desc.get("inputSchema", {}))
        self._parent = parent

    @property
    def parameters(self) -> dict:
        """Return the MCP-provided input schema (title/$defs stripped)."""
        schema = dict(self._input_schema)
        schema.pop("title", None)
        schema.pop("$defs", None)
        return schema

    def parse_args(self, raw: dict) -> dict:
        """Pass through without Pydantic validation — schema comes from MCP."""
        return raw

    def execute(self, args: Any) -> str:
        """Delegate execution to the parent MCPServerTool."""
        return self._parent.call_tool(self.mcp_tool_name, args)
