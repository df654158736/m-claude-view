import pytest
from src.infrastructure.tools.bash import BashTool


def test_bash_tool_execute():
    """Test bash tool can execute commands."""
    tool = BashTool()
    result = tool.execute(command="echo hello")
    assert "hello" in result


def test_bash_tool_name():
    """Test bash tool has correct name."""
    tool = BashTool()
    assert tool.name == "bash"


def test_bash_tool_schema():
    """Test bash tool generates correct schema."""
    tool = BashTool()
    assert "command" in tool.parameters["properties"]
    assert "timeout" in tool.parameters["properties"]
