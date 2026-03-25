import json
import sys
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.tools.mcp_server import MCPServerTool


def test_mcp_server_tool_stdio():
    fake_server = Path(__file__).parent / "fake_mcp_server.py"
    tool = MCPServerTool(
        server_name="fake",
        server_conf={
            "type": "stdio",
            "command": sys.executable,
            "args": [str(fake_server)],
        },
    )
    result = tool.execute(action="list_tools", timeout=10)
    payload = json.loads(result)
    assert payload["tools"][0]["name"] == "browser_navigate"
    tool.close()


def test_mcp_server_tool_http():
    class FakeResp:
        def __init__(self, text: str):
            self._text = text
            self.headers = {}

        def read(self):
            return self._text.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(req, timeout=10):  # noqa: ARG001
        body = json.loads(req.data.decode("utf-8"))
        req_id = body.get("id")
        method = body.get("method")
        if method == "initialize":
            payload = {"jsonrpc": "2.0", "id": req_id, "result": {"protocolVersion": "2024-11-05"}}
        elif method == "tools/list":
            payload = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": [{"name": "http_tool"}]}}
        else:
            payload = {"jsonrpc": "2.0", "id": req_id, "result": {"ok": True}}
        sse = f"event: message\ndata: {json.dumps(payload)}\n\n"
        return FakeResp(sse)

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        tool = MCPServerTool(
            server_name="httpfake",
            server_conf={"type": "http", "url": "http://localhost:9999/mcp"},
        )
        result = tool.execute(action="list_tools", timeout=10)
        payload = json.loads(result)
        assert payload["tools"][0]["name"] == "http_tool"
        tool.close()
