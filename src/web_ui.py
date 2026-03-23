"""Simple web UI for visualizing packet logs."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_PATH = PROJECT_ROOT / "logs" / "packets.jsonl"
HTML_PATH = PROJECT_ROOT / "web" / "dashboard.html"


def read_packets(log_path: Path, limit: int = 300) -> list[dict]:
    """Read latest packet lines from a JSONL log file."""
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


def group_packets_by_user(packets: list[dict]) -> list[dict]:
    """Group packets by each user question packet."""
    groups: list[dict] = []
    current = None

    for packet in packets:
        packet_type = packet.get("type")
        if packet_type == "user":
            current = {
                "question": packet.get("content", ""),
                "iteration": packet.get("iteration", 0),
                "packets": [packet],
            }
            groups.append(current)
            continue

        if current is None:
            current = {"question": "(startup)", "iteration": 0, "packets": []}
            groups.append(current)
        current["packets"].append(packet)

    for idx, group in enumerate(groups, start=1):
        type_counts: dict[str, int] = {}
        for p in group["packets"]:
            p_type = p.get("type", "unknown")
            type_counts[p_type] = type_counts.get(p_type, 0) + 1
        group["id"] = idx
        group["packet_count"] = len(group["packets"])
        group["type_counts"] = type_counts

    return groups


def clear_packet_log(log_path: Path) -> None:
    """Clear packet log file content."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")


def build_handler(log_path: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._serve_html()
                return
            if parsed.path == "/api/packets":
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["300"])[0])
                packets = read_packets(log_path, limit=limit)
                payload = {
                    "log_path": str(log_path),
                    "packets": packets,
                }
                self._serve_json(payload)
                return
            if parsed.path == "/api/groups":
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["300"])[0])
                packets = read_packets(log_path, limit=limit)
                payload = {
                    "log_path": str(log_path),
                    "groups": group_packets_by_user(packets),
                }
                self._serve_json(payload)
                return
            self.send_error(404, "Not Found")

        def do_POST(self):
            parsed = urlparse(self.path)
            if parsed.path == "/api/clear":
                clear_packet_log(log_path)
                self._serve_json({"ok": True, "log_path": str(log_path)})
                return
            self.send_error(404, "Not Found")

        def log_message(self, format, *args):  # noqa: A003
            return

        def _serve_html(self):
            if not HTML_PATH.exists():
                self.send_error(500, "dashboard.html not found")
                return
            body = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _serve_json(self, payload: dict):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Run packet log web dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_PATH))
    args = parser.parse_args()

    log_path = Path(args.log_file)
    handler_cls = build_handler(log_path)
    server = ThreadingHTTPServer((args.host, args.port), handler_cls)

    print(f"Dashboard running on http://{args.host}:{args.port}")
    print(f"Reading packet log file: {log_path}")
    server.serve_forever()


if __name__ == "__main__":
    main()
