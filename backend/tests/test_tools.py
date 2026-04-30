import pytest
from pydantic import BaseModel, Field
from src.infrastructure.tools.base import Tool
from src.infrastructure.tools.registry import ToolRegistry


def test_tool_registry_register():
    """Test tool can be registered."""
    registry = ToolRegistry()

    class MockTool(Tool):
        name = "mock_tool"
        description = "A mock tool"

        def execute(self, args):
            return "executed"

    registry.register(MockTool())
    assert "mock_tool" in registry._tools


def test_tool_registry_get_schema():
    """Test tool schema generation."""
    registry = ToolRegistry()

    class MockTool(Tool):
        name = "mock_tool"
        description = "A mock tool"

        class Input(BaseModel):
            query: str = Field(description="test query")

        def execute(self, args):
            return "executed"

    registry.register(MockTool())
    schema = registry.get_tool_schemas()

    assert len(schema) == 1
    assert schema[0]["function"]["name"] == "mock_tool"
    assert "query" in schema[0]["function"]["parameters"]["properties"]


def test_tool_registry_execute():
    """Test tool execution."""
    registry = ToolRegistry()

    class MockTool(Tool):
        name = "mock_tool"
        description = "A mock tool"

        def execute(self, args):
            return "executed"

    registry.register(MockTool())
    result = registry.execute("mock_tool", {})
    assert result == "executed"
