"""Tool setup helpers shared by CLI and HTTP service.

Built-in tools are auto-discovered via ``Tool.__init_subclass__``.
Any module under ``infrastructure/tools/builtin/`` that defines a
``Tool`` subclass with a non-empty ``name`` is automatically imported.
New tools only need to:
  1. Create a file in ``tools/builtin/`` (e.g. ``read_file.py``).
  2. Define a ``Tool`` subclass with ``name = "read_file"``.
  3. Add ``name: read_file`` + ``enabled: true`` in ``config.yaml``.

MCP tools use lazy loading: sub-tools are discovered at startup and
stored in a deferred catalog.  The LLM sees only tool names in the
system prompt and uses ``load_mcp_tools`` to fetch full schemas on
demand before calling them.
"""
import importlib
import logging
import pkgutil

import src.infrastructure.tools as _tools_pkg
from src.infrastructure.tools.base import Tool
from src.infrastructure.tools.builtin.load_mcp_tools import LoadMcpToolsTool
from src.infrastructure.tools.mcp_server import MCPServerTool
from src.infrastructure.tools.mcp_sub_tool import MCPSubTool
from src.infrastructure.tools.registry import ToolRegistry


logger = logging.getLogger("react_agent")


def _import_all_tool_modules() -> None:
    """Recursively import every module in the tools package so subclasses register."""
    for module_info in pkgutil.walk_packages(_tools_pkg.__path__, _tools_pkg.__name__ + "."):
        try:
            importlib.import_module(module_info.name)
        except Exception:  # noqa: BLE001
            logger.debug("Skipped tool module %s", module_info.name)


def setup_tools(config) -> ToolRegistry:
    """Setup tool registry with configured tools."""
    _import_all_tool_modules()

    registry = ToolRegistry()

    for tool_config in config.tools:
        if not tool_config.enabled:
            continue

        tool_cls = Tool.get_class(tool_config.name)
        if tool_cls is None:
            logger.warning("Unknown tool: %s (not found in registry: %s)", tool_config.name, Tool.registered_names())
            continue
        registry.register(tool_cls())
        logger.info("Registered tool: %s", tool_config.name)

    # MCP servers: discover sub-tools and register them as deferred catalog
    # config.mcp is already the servers dict (extracted by settings.py)
    mcp_servers = getattr(config, "mcp", None) or {}
    if isinstance(mcp_servers, dict) and "servers" in mcp_servers:
        mcp_servers = mcp_servers["servers"]

    for server_name, server_conf in mcp_servers.items():
        try:
            mcp_tool = MCPServerTool(server_name=server_name, server_conf=server_conf)
            tool_descs = mcp_tool.list_tools(timeout=30)
            sub_tools = [
                MCPSubTool(server_name=server_name, mcp_tool_desc=desc, parent=mcp_tool)
                for desc in tool_descs
            ]
            registry.register_mcp_catalog(server_name, sub_tools)
            logger.info(
                "MCP server '%s': discovered %d tools (deferred)",
                server_name, len(sub_tools),
            )
        except Exception as err:  # noqa: BLE001
            logger.warning("Failed to discover MCP tools from '%s': %s", server_name, err)

    # Register the meta-tool for loading MCP schemas on demand
    if registry.get_mcp_catalog():
        load_tool = LoadMcpToolsTool(registry=registry)
        registry.register(load_tool)
        logger.info("Registered load_mcp_tools meta-tool (%d deferred tools)", len(registry.get_mcp_catalog()))

    return registry
