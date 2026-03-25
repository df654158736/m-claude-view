"""Packet log read/write and grouping helpers for web dashboard."""
from __future__ import annotations

import json
from pathlib import Path


def read_packets(log_path: Path, limit: int = 300) -> list[dict]:
    """Read latest packet records from JSONL file."""
    if not log_path.exists():
        return []

    lines = [line for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = lines[-limit:] if limit > 0 else lines
    packets: list[dict] = []
    for line in selected:
        try:
            packets.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return packets


def clear_packet_log(log_path: Path) -> None:
    """Clear packet log file content."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")


def group_packets_by_user(packets: list[dict], merge_same_question: bool = True) -> list[dict]:
    """Backward-compatible grouping by user message for tests and legacy API."""
    raw_groups: list[dict] = []
    current = None

    for packet in packets:
        packet_type = packet.get("type")
        if packet_type == "user":
            current = {
                "question": packet.get("content", ""),
                "iteration": packet.get("iteration", 0),
                "packets": [packet],
            }
            raw_groups.append(current)
            continue

        if current is None:
            current = {"question": "(startup)", "iteration": 0, "packets": []}
            raw_groups.append(current)
        current["packets"].append(packet)

    if not merge_same_question:
        groups = raw_groups
    else:
        groups = []
        by_question: dict[str, dict] = {}
        for group in raw_groups:
            key = group["question"] or "(empty)"
            if key not in by_question:
                merged = {
                    "question": key,
                    "iteration": group["iteration"],
                    "packets": [],
                    "runs": 0,
                }
                by_question[key] = merged
                groups.append(merged)
            by_question[key]["packets"].extend(group["packets"])
            by_question[key]["runs"] += 1

    for idx, group in enumerate(groups, start=1):
        type_counts: dict[str, int] = {}
        for packet in group["packets"]:
            packet_type = packet.get("type", "unknown")
            type_counts[packet_type] = type_counts.get(packet_type, 0) + 1
        group["id"] = idx
        group["packet_count"] = len(group["packets"])
        group["type_counts"] = type_counts
        group.setdefault("runs", 1)

    return groups


def build_runs(packets: list[dict]) -> list[dict]:
    """Build chronological runs where each run starts from one user packet."""
    runs: list[dict] = []
    current: dict | None = None

    for packet in packets:
        packet_type = packet.get("type")
        if packet_type == "user":
            run_id = len(runs) + 1
            current = {
                "id": run_id,
                "question": packet.get("content", ""),
                "events": [packet],
                "start_iteration": packet.get("iteration", 0),
            }
            runs.append(current)
            continue

        if current is None:
            current = {
                "id": len(runs) + 1,
                "question": "(startup)",
                "events": [],
                "start_iteration": 0,
            }
            runs.append(current)

        current["events"].append(packet)

    for run in runs:
        event_types: dict[str, int] = {}
        for event in run["events"]:
            event_type = event.get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1

        run["event_count"] = len(run["events"])
        run["type_counts"] = event_types

        final_answer = None
        for event in reversed(run["events"]):
            if event.get("type") == "llm_response" and event.get("content"):
                final_answer = event["content"]
                break
        run["final_answer"] = final_answer

    return runs
