import json
from pathlib import Path

from src.application.services.agent_task_service import AgentTaskService
from src.infrastructure.storage.packet_log_repo import clear_packet_log, group_packets_by_user, read_packets


def test_read_packets_reads_valid_jsonl(tmp_path):
    log_file = tmp_path / "packets.jsonl"
    log_file.write_text(
        "\n".join(
            [
                json.dumps({"type": "user", "iteration": 0}),
                "not-json",
                json.dumps({"type": "llm_request", "iteration": 1}),
            ]
        ),
        encoding="utf-8",
    )

    packets = read_packets(log_file, limit=10)
    assert len(packets) == 2
    assert packets[0]["type"] == "user"
    assert packets[1]["type"] == "llm_request"


def test_read_packets_handles_missing_file(tmp_path):
    missing = tmp_path / "missing.jsonl"
    packets = read_packets(missing)
    assert packets == []


def test_group_packets_by_user():
    packets = [
        {"type": "user", "iteration": 0, "content": "问题1"},
        {"type": "llm_request", "iteration": 1},
        {"type": "llm_response", "iteration": 1},
        {"type": "tool", "iteration": 1},
        {"type": "user", "iteration": 0, "content": "问题2"},
        {"type": "llm_request", "iteration": 1},
    ]
    groups = group_packets_by_user(packets)

    assert len(groups) == 2
    assert groups[0]["question"] == "问题1"
    assert groups[0]["packet_count"] == 4
    assert groups[0]["type_counts"]["tool"] == 1
    assert groups[1]["question"] == "问题2"
    assert groups[1]["packet_count"] == 2


def test_group_packets_by_user_merges_same_question():
    packets = [
        {"type": "user", "iteration": 0, "content": "同一个问题"},
        {"type": "llm_request", "iteration": 1},
        {"type": "user", "iteration": 0, "content": "同一个问题"},
        {"type": "llm_response", "iteration": 1},
    ]
    groups = group_packets_by_user(packets, merge_same_question=True)
    assert len(groups) == 1
    assert groups[0]["question"] == "同一个问题"
    assert groups[0]["runs"] == 2
    assert groups[0]["packet_count"] == 4


def test_clear_packet_log(tmp_path):
    log_file = tmp_path / "packets.jsonl"
    log_file.write_text('{"type":"user"}\n', encoding="utf-8")
    clear_packet_log(log_file)
    assert log_file.read_text(encoding="utf-8") == ""


def test_agent_service_submit_and_complete():
    class FakeEngine:
        def run(self, task: str) -> str:
            return f"ok:{task}"

    service = AgentTaskService(engine=FakeEngine())
    task_id = service.submit("hello")

    # wait briefly for background worker
    for _ in range(20):
        task = service.get(task_id)
        if task and task["status"] == "done":
            break
        import time
        time.sleep(0.02)

    task = service.get(task_id)
    assert task is not None
    assert task["status"] == "done"
    assert task["result"] == "ok:hello"


def test_agent_service_clear_resets_engine_session():
    class FakeEngine:
        def __init__(self):
            self.reset_called = False

        def reset_session(self):
            self.reset_called = True

    engine = FakeEngine()
    service = AgentTaskService(engine=engine)
    service.clear()

    assert engine.reset_called is True
