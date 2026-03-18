import pytest
from unittest.mock import Mock, MagicMock
from src.react_engine import ReActEngine


def test_react_engine_initialization():
    """Test ReAct engine can be initialized."""
    llm_client = Mock()
    tool_registry = Mock()
    config = Mock()
    config.max_iterations = 10
    config.temperature = 0.7

    engine = ReActEngine(llm_client, tool_registry, config)
    assert engine.max_iterations == 10


def test_react_engine_build_messages():
    """Test message building with system prompt."""
    llm_client = Mock()
    tool_registry = Mock()
    tool_registry.get_tool_schemas.return_value = []

    config = Mock()
    config.max_iterations = 10
    config.temperature = 0.7

    engine = ReActEngine(llm_client, tool_registry, config)
    messages = engine.build_messages("test task")

    assert messages[0]["role"] == "system"
    assert "test task" in messages[1]["content"]