"""Tool setup helpers shared by CLI and HTTP service.

Built-in tools are auto-discovered via ``Tool.__init_subclass__``.
Any module under ``infrastructure/tools/builtin/`` that defines a
``Tool`` subclass with a non-empty ``name`` is automatically imported.
New tools only need to:
  1. Create a file in ``tools/builtin/`` (e.g. ``read_file.py``).
  2. Define a ``Tool`` subclass with ``name = "read_file"``.
  3. Add ``name: read_file`` + ``enabled: true`` in ``config.yaml``.
"""
import importlib
import logging
import pkgutil

import src.infrastructure.tools as _tools_pkg
from src.infrastructure.tools.base import Tool
from src.infrastructure.tools.mcp_server import MCPServerTool
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
    enabled_tool_names = {tool.name for tool in config.tools if tool.enabled}

    for tool_config in config.tools:
        if not tool_config.enabled:
            continue
        if tool_config.name.endswith("_mcp"):
            continue

        tool_cls = Tool.get_class(tool_config.name)
        if tool_cls is None:
            logger.warning("Unknown tool: %s (not found in registry: %s)", tool_config.name, Tool.registered_names())
            continue
        registry.register(tool_cls())
        logger.info("Registered tool: %s", tool_config.name)

    for server_name, server_conf in config.mcp.items():
        tool_name = f"{server_name}_mcp"
        if enabled_tool_names and tool_name not in enabled_tool_names:
            continue
        try:
            registry.register(MCPServerTool(server_name=server_name, server_conf=server_conf))
            logger.info("Registered MCP tool: %s", tool_name)
        except (TypeError, ValueError) as err:
            logger.warning("Failed to register %s: %s", tool_name, err)

    return registry
