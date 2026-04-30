from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from src.infrastructure.tools.factory import setup_tools


def test_setup_tools_registers_builtin():
    config = SimpleNamespace(
        tools=[
            SimpleNamespace(name="bash", enabled=True),
        ],
        mcp={"servers": {}},
    )

    registry = setup_tools(config)
    assert "bash" in registry._tools


def test_setup_tools_defers_mcp_tools():
    fake_tool_descs = [
        {"name": "browser_navigate", "description": "Navigate", "inputSchema": {"type": "object"}},
        {"name": "browser_click", "description": "Click", "inputSchema": {"type": "object"}},
    ]

    with patch("src.infrastructure.tools.factory.MCPServerTool") as MockMCP:
        mock_instance = MagicMock()
        mock_instance.list_tools.return_value = fake_tool_descs
        MockMCP.return_value = mock_instance

        config = SimpleNamespace(
            tools=[
                SimpleNamespace(name="bash", enabled=True),
            ],
            mcp={"servers": {"playwright": {"type": "http", "url": "http://localhost/mcp"}}},
        )

        registry = setup_tools(config)
        assert "bash" in registry._tools
        assert "load_mcp_tools" in registry._tools
        catalog = registry.get_mcp_catalog()
        names = [e["name"] for e in catalog]
        assert "playwright__browser_navigate" in names
        assert "playwright__browser_click" in names
