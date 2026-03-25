"""A tiny fake MCP stdio server for tests."""
from __future__ import annotations

import json
import sys


CALL_COUNT = 0


def read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        key, _, value = line.decode("utf-8").partition(":")
        headers[key.lower().strip()] = value.strip()
    content_length = int(headers.get("content-length", "0"))
    body = sys.stdin.buffer.read(content_length)
    if not body:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(payload):
    body = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    sys.stdout.buffer.write(header + body)
    sys.stdout.buffer.flush()


def main():
    global CALL_COUNT

    while True:
        msg = read_message()
        if msg is None:
            return
        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})

        if req_id is None:
            continue

        if method == "initialize":
            write_message({"jsonrpc": "2.0", "id": req_id, "result": {"serverInfo": {"name": "fake"}}})
        elif method == "tools/list":
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": [{"name": "browser_navigate", "description": "fake navigate"}]},
                }
            )
        elif method == "tools/call":
            CALL_COUNT += 1
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"called:{params.get('name')}"}],
                        "call_count": CALL_COUNT,
                        "arguments": params.get("arguments", {}),
                    },
                }
            )
        else:
            write_message(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            )


if __name__ == "__main__":
    main()
