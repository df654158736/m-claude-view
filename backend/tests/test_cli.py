from types import SimpleNamespace

from src.infrastructure.tools.factory import setup_tools


def test_setup_tools_registers_playwright_mcp():
    config = SimpleNamespace(
        tools=[
            SimpleNamespace(name="bash", enabled=True),
            SimpleNamespace(name="playwright_mcp", enabled=True),
        ],
        mcp={
            "playwright": {
                "command": "npx",
                "args": ["-y", "@playwright/mcp@latest"],
                "env": {},
            }
        },
    )

    registry = setup_tools(config)
    assert "bash" in registry._tools
    assert "playwright_mcp" in registry._tools
