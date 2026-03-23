import json
from pathlib import Path

from src.web_ui import clear_packet_log, group_packets_by_user, read_packets


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


def test_clear_packet_log(tmp_path):
    log_file = tmp_path / "packets.jsonl"
    log_file.write_text('{"type":"user"}\n', encoding="utf-8")
    clear_packet_log(log_file)
    assert log_file.read_text(encoding="utf-8") == ""
