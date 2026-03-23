from unittest.mock import Mock, patch
from pathlib import Path
import json
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


def test_react_engine_logs_message_types():
    """Test engine logs detailed packets with user/agent/tool types."""
    llm_client = Mock()
    tool_registry = Mock()
    config = Mock()
    config.max_iterations = 2
    config.temperature = 0.7

    tool_registry.get_tool_schemas.return_value = [{"type": "function"}]
    tool_registry.execute.return_value = "Exit code: 0\nOutput:\nhello"

    first_response = Mock()
    second_response = Mock()

    llm_client.chat.side_effect = [first_response, second_response]
    tool_call = Mock()
    tool_call.id = "call_1"
    tool_call.name = "bash"
    tool_call.arguments = {"command": "echo hello"}

    llm_client.parse_response.side_effect = [(None, [tool_call]), ("done", [])]

    engine = ReActEngine(llm_client, tool_registry, config)

    with patch("src.react_engine.logger") as mock_logger:
        result = engine.run("say hello")

    assert result == "done"

    logged = "\n".join(str(call.args[0]) for call in mock_logger.info.call_args_list if call.args)
    assert ('"type":"user"' in logged) or ('"type": "user"' in logged)
    assert ('"type":"llm_request"' in logged) or ('"type": "llm_request"' in logged)
    assert ('"type":"llm_response"' in logged) or ('"type": "llm_response"' in logged)
    assert ('"type":"agent"' in logged) or ('"type": "agent"' in logged)
    assert ('"type":"tool"' in logged) or ('"type": "tool"' in logged)


def test_react_engine_readable_mode_logs():
    """Test engine emits readable log lines in both mode."""
    llm_client = Mock()
    tool_registry = Mock()
    config = Mock()
    config.max_iterations = 1
    config.temperature = 0.7
    config.packet_log_mode = "both"
    config.color_logs = True

    tool_registry.get_tool_schemas.return_value = []
    llm_client.chat.return_value = Mock()
    llm_client.parse_response.return_value = ("done", [])

    engine = ReActEngine(llm_client, tool_registry, config)

    with patch("src.react_engine.logger") as mock_logger:
        result = engine.run("hello")

    assert result == "done"
    logged = "\n".join(str(call.args[0]) for call in mock_logger.info.call_args_list if call.args)
    assert "[USER]" in logged
    assert "[TO_LLM]" in logged
    assert "[FROM_LLM]" in logged
    assert "\x1b[" in logged


def test_react_engine_pretty_json_logs():
    """Test engine can output pretty-formatted JSON packets."""
    llm_client = Mock()
    tool_registry = Mock()
    config = Mock()
    config.max_iterations = 1
    config.temperature = 0.7
    config.packet_log_mode = "json"
    config.json_pretty = True
    config.json_indent = 2

    tool_registry.get_tool_schemas.return_value = []
    llm_client.chat.return_value = Mock()
    llm_client.parse_response.return_value = ("done", [])

    engine = ReActEngine(llm_client, tool_registry, config)

    with patch("src.react_engine.logger") as mock_logger:
        result = engine.run("hello")

    assert result == "done"
    logged = "\n".join(str(call.args[0]) for call in mock_logger.info.call_args_list if call.args)
    assert "{\n" in logged
    assert '\n  "type": "user"' in logged


def test_react_engine_writes_packet_log_file(tmp_path):
    """Test engine writes machine-readable packet logs to file."""
    llm_client = Mock()
    tool_registry = Mock()
    config = Mock()
    config.max_iterations = 1
    config.packet_log_mode = "readable"
    config.packet_log_file = str(tmp_path / "packets.jsonl")

    tool_registry.get_tool_schemas.return_value = []
    llm_client.chat.return_value = Mock()
    llm_client.parse_response.return_value = ("done", [])

    engine = ReActEngine(llm_client, tool_registry, config)
    engine.run("hello packets")

    log_path = Path(config.packet_log_file)
    assert log_path.exists()
    lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 2

    first = json.loads(lines[0])
    assert first["type"] == "user"


def test_react_engine_keeps_session_history_across_runs():
    """Second run should include prior turns in llm_request messages."""
    llm_client = Mock()
    tool_registry = Mock()
    config = Mock()
    config.max_iterations = 1
    config.packet_log_mode = "json"

    tool_registry.get_tool_schemas.return_value = []
    llm_client.chat.side_effect = [Mock(), Mock()]
    llm_client.parse_response.side_effect = [("first answer", []), ("second answer", [])]

    engine = ReActEngine(llm_client, tool_registry, config)

    with patch("src.react_engine.logger") as mock_logger:
        engine.run("first question")
        engine.run("second question")

    packets = []
    for call in mock_logger.info.call_args_list:
        if not call.args:
            continue
        msg = str(call.args[0])
        try:
            packets.append(json.loads(msg))
        except json.JSONDecodeError:
            continue

    llm_requests = [p for p in packets if p.get("type") == "llm_request"]
    assert len(llm_requests) >= 2
    second_messages = llm_requests[-1]["messages"]

    roles_and_content = [(m.get("role"), m.get("content")) for m in second_messages]
    assert ("user", "first question") in roles_and_content
    assert ("assistant", "first answer") in roles_and_content
    assert ("user", "second question") in roles_and_content
