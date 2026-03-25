"""Tool setup helpers shared by CLI and HTTP service."""
import logging

from src.infrastructure.tools.bash import BashTool
from src.infrastructure.tools.mcp_server import MCPServerTool
from src.infrastructure.tools.registry import ToolRegistry


logger = logging.getLogger("react_agent")


def setup_tools(config):
    """Setup tool registry with configured tools."""
    registry = ToolRegistry()
    enabled_tool_names = {tool.name for tool in config.tools if tool.enabled}

    for tool_config in config.tools:
        if not tool_config.enabled:
            continue

        if tool_config.name == "bash":
            registry.register(BashTool())
            logger.info("Registered bash tool")
        elif tool_config.name.endswith("_mcp"):
            continue
        else:
            logger.warning("Unknown tool: %s", tool_config.name)

    for server_name, server_conf in config.mcp.items():
        tool_name = f"{server_name}_mcp"
        if enabled_tool_names and tool_name not in enabled_tool_names:
            continue
        try:
            registry.register(MCPServerTool(server_name=server_name, server_conf=server_conf))
            logger.info("Registered %s tool", tool_name)
        except (TypeError, ValueError) as err:
            logger.warning("Failed to register %s: %s", tool_name, err)

    return registry
