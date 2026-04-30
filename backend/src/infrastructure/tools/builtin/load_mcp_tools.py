"""Meta-tool for searching and activating deferred MCP sub-tools."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from src.infrastructure.tools.base import Tool

if TYPE_CHECKING:
    from src.infrastructure.tools.registry import ToolRegistry


class LoadMcpToolsTool(Tool):
    """Search the MCP tool catalog and activate matching tools."""

    name = "load_mcp_tools"
    description = (
        "Search and load MCP tool schemas by keyword or exact names, "
        "making them available for direct calling. "
        'Use query "select:tool1,tool2" to load specific tools by name, '
        "or pass a keyword to search tool names and descriptions. "
        "Returns the full JSON schemas of activated tools."
    )

    class Input(BaseModel):
        query: str = Field(
            description=(
                'Tool name or keyword to search. '
                'Use "select:name1,name2" to load specific tools by exact name, '
                'or a keyword string to search names and descriptions.'
            ),
        )
        max_results: int = Field(
            default=5,
            description="Maximum number of results to return.",
        )

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, args: Input) -> str:
        query = args.query.strip()

        if query.startswith("select:"):
            names = [n.strip() for n in query[len("select:"):].split(",") if n.strip()]
            activated = self._registry.activate_mcp_tools(names)
            if not activated:
                catalog = self._registry.get_mcp_catalog()
                return json.dumps(
                    {
                        "error": "No tools matched the given names.",
                        "available": catalog,
                    },
                    ensure_ascii=False,
                )
            return json.dumps({"activated": activated}, ensure_ascii=False)

        # Keyword search
        matches = self._registry.search_mcp_catalog(query)
        matches = matches[: args.max_results]

        if not matches:
            catalog = self._registry.get_mcp_catalog()
            return json.dumps(
                {
                    "message": f"No tools matched query '{query}'.",
                    "available": catalog,
                },
                ensure_ascii=False,
            )

        names = [m["name"] for m in matches]
        activated = self._registry.activate_mcp_tools(names)
        return json.dumps({"activated": activated}, ensure_ascii=False)
