"""Generic MCP server tool with stdio/http transport support."""
from __future__ import annotations

import atexit
import json
import os
import select
import socket
import subprocess
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from typing import Any

from src.infrastructure.tools.base import Tool


class MCPServerTool(Tool):
    """A generic MCP server adapter."""

    _mcp_parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_tools", "call_tool"],
                "description": "执行动作：列出工具或调用具体工具",
            },
            "tool_name": {
                "type": "string",
                "description": "当 action=call_tool 时必填，例如 browser_navigate",
            },
            "arguments": {
                "type": "object",
                "description": "传给 MCP 工具的参数对象",
                "default": {},
            },
            "timeout": {
                "type": "number",
                "description": "超时时间（秒），默认 60",
                "default": 60,
            },
        },
        "required": ["action"],
    }

    @property
    def parameters(self) -> dict:
        return self._mcp_parameters

    def __init__(self, server_name: str, server_conf: dict):
        self.server_name = server_name
        self.name = f"{server_name}_mcp"
        self.description = f"通过 MCP Server '{server_name}' 执行 tools/list 与 tools/call"

        self.server_type = server_conf.get("type", "stdio")
        self.command = server_conf.get("command")
        self.args = server_conf.get("args", [])
        self.env = server_conf.get("env", {})
        self.url = server_conf.get("url")
        self.ready_timeout = int(server_conf.get("ready_timeout", 20))

        self._req_id = 0
        self._proc: subprocess.Popen | None = None
        self._initialized = False
        self._http_session_id: str | None = None
        if self.server_type == "http" and self.command:
            self._prepare_managed_http_endpoint()
        atexit.register(self.close)

    def execute(self, args: Any) -> str:
        kwargs = args if isinstance(args, dict) else {}
        action = str(kwargs.get("action", ""))
        tool_name_raw = kwargs.get("tool_name")
        tool_name = str(tool_name_raw) if tool_name_raw is not None else None
        arguments_raw = kwargs.get("arguments")
        arguments = arguments_raw if isinstance(arguments_raw, dict) else {}
        timeout_raw = kwargs.get("timeout", 60)
        try:
            timeout = int(timeout_raw)
        except (TypeError, ValueError):
            timeout = 60

        if action not in {"list_tools", "call_tool"}:
            return f"Error: Unsupported action '{action}'"
        if action == "call_tool" and not tool_name:
            return "Error: tool_name is required when action=call_tool"

        deadline = time.monotonic() + timeout
        try:
            if self.server_type == "http":
                return self._execute_http(action, tool_name, arguments, deadline)
            return self._execute_stdio(action, tool_name, arguments, deadline)
        except TimeoutError as e:
            self.close()
            return f"Error: {e}"
        except (ValueError, OSError, urllib.error.URLError) as e:
            self.close()
            return f"Error: MCP protocol failed: {e}"

    def close(self) -> None:
        if not self._proc:
            return
        self._proc.terminate()
        try:
            self._proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        finally:
            self._proc = None
            self._initialized = False
            self._http_session_id = None

    def _execute_stdio(self, action: str, tool_name: str | None, arguments: dict, deadline: float) -> str:
        proc = self._ensure_stdio_session(deadline)
        if action == "list_tools":
            result = self._stdio_request(proc, "tools/list", {}, deadline)
        else:
            result = self._stdio_request(
                proc,
                "tools/call",
                {"name": tool_name, "arguments": arguments},
                deadline,
            )
        if "error" in result:
            return f"Error: MCP request failed: {json.dumps(result['error'], ensure_ascii=False)}"
        return json.dumps(result.get("result", {}), ensure_ascii=False, indent=2)

    def _execute_http(self, action: str, tool_name: str | None, arguments: dict, deadline: float) -> str:
        self._ensure_http_session(deadline)
        if action == "list_tools":
            result = self._http_request("tools/list", {}, deadline)
        else:
            result = self._http_request(
                "tools/call",
                {"name": tool_name, "arguments": arguments},
                deadline,
            )
            if (
                tool_name == "browser_navigate"
                and "result" in result
                and result["result"].get("status") == "accepted"
            ):
                # Playwright MCP streamable HTTP may acknowledge navigate with empty body.
                # Follow up with a snapshot call to provide meaningful output.
                snapshot_result = None
                for _ in range(3):
                    try:
                        snapshot = self._http_request(
                            "tools/call",
                            {"name": "browser_snapshot", "arguments": {}},
                            deadline,
                        )
                        if "result" in snapshot:
                            snapshot_result = snapshot["result"]
                            break
                    except (TimeoutError, urllib.error.URLError, ValueError):
                        time.sleep(0.7)
                        continue
                if snapshot_result is not None:
                    result["result"]["followup_snapshot"] = snapshot_result
                else:
                    result["result"]["note"] = "navigation accepted; no immediate snapshot was returned"
        if "error" in result:
            return f"Error: MCP request failed: {json.dumps(result['error'], ensure_ascii=False)}"
        return json.dumps(result.get("result", {}), ensure_ascii=False, indent=2)

    def _ensure_stdio_session(self, deadline: float) -> subprocess.Popen:
        if self._proc and self._proc.poll() is not None:
            self._proc = None
            self._initialized = False

        if not self._proc:
            if not self.command:
                raise ValueError(f"{self.server_name}: command is required for stdio transport")
            merged_env = os.environ.copy()
            merged_env.update({k: str(v) for k, v in self.env.items()})
            self._proc = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=merged_env,
            )

        if not self._initialized:
            init_resp = self._stdio_request(
                self._proc,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mclaude", "version": "0.1.0"},
                },
                deadline,
            )
            if "error" in init_resp:
                raise ValueError(f"MCP initialize failed: {json.dumps(init_resp['error'], ensure_ascii=False)}")
            self._stdio_notify(self._proc, "notifications/initialized", {})
            self._initialized = True
        return self._proc

    def _ensure_http_session(self, deadline: float) -> None:
        if self._proc and self._proc.poll() is not None:
            self._proc = None
            self._initialized = False

        if self.command and not self._proc:
            merged_env = os.environ.copy()
            merged_env.update({k: str(v) for k, v in self.env.items()})
            self._proc = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=merged_env,
            )
            # Give the HTTP server some startup time.
            start_deadline = min(deadline, time.monotonic() + self.ready_timeout)
            while time.monotonic() < start_deadline:
                try:
                    self._http_request("initialize", {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "mclaude", "version": "0.1.0"},
                    }, deadline=time.monotonic() + 3)
                    try:
                        self._http_notify("notifications/initialized", {}, deadline=time.monotonic() + 2)
                    except (TimeoutError, urllib.error.URLError, ValueError):
                        # Some servers do not require/accept explicit initialized notification on HTTP transport.
                        pass
                    self._initialized = True
                    break
                except (TimeoutError, urllib.error.URLError, ValueError):
                    time.sleep(0.3)
            if not self._initialized:
                raise TimeoutError(f"{self.server_name}: HTTP MCP server startup timed out")

        if not self.url:
            raise ValueError(f"{self.server_name}: url is required for http transport")

        if not self._initialized:
            init_resp = self._http_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mclaude", "version": "0.1.0"},
                },
                deadline,
            )
            if "error" in init_resp:
                raise ValueError(f"MCP initialize failed: {json.dumps(init_resp['error'], ensure_ascii=False)}")
            try:
                self._http_notify("notifications/initialized", {}, deadline)
            except (TimeoutError, urllib.error.URLError, ValueError):
                pass
            self._initialized = True

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _stdio_notify(self, proc: subprocess.Popen, method: str, params: dict) -> None:
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        self._stdio_write(proc, msg)

    def _stdio_request(self, proc: subprocess.Popen, method: str, params: dict, deadline: float) -> dict:
        req_id = self._next_id()
        msg = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        self._stdio_write(proc, msg)
        while True:
            payload = self._stdio_read(proc, deadline)
            if payload.get("id") == req_id:
                return payload

    def _stdio_write(self, proc: subprocess.Popen, payload: dict) -> None:
        if not proc.stdin:
            raise ValueError("MCP stdin is not available")
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        proc.stdin.write(header + body)
        proc.stdin.flush()

    def _stdio_read(self, proc: subprocess.Popen, deadline: float) -> dict:
        if not proc.stdout:
            raise ValueError("MCP stdout is not available")
        header_text = self._read_headers(proc.stdout, deadline)
        content_length = None
        for line in header_text.splitlines():
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":", 1)[1].strip())
                break
        if content_length is None:
            raise ValueError(f"Invalid MCP header: {header_text!r}")
        body = self._read_exact(proc.stdout.fileno(), content_length, deadline)
        return json.loads(body.decode("utf-8"))

    def _http_notify(self, method: str, params: dict, deadline: float) -> None:
        self._http_send({"jsonrpc": "2.0", "method": method, "params": params}, deadline, expect_response=False)

    def _http_request(self, method: str, params: dict, deadline: float) -> dict:
        req_id = self._next_id()
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        return self._http_send(payload, deadline, expect_response=True, request_id=req_id)

    def _http_send(
        self,
        payload: dict,
        deadline: float,
        expect_response: bool,
        request_id: int | None = None,
    ) -> dict:
        if not self.url:
            raise ValueError(f"{self.server_name}: url is required for http transport")
        timeout = max(0.1, deadline - time.monotonic())
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self._http_session_id:
            req.add_header("Mcp-Session-Id", self._http_session_id)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            session_id = resp.headers.get("mcp-session-id")
            if session_id:
                self._http_session_id = session_id
            raw = resp.read().decode("utf-8", errors="replace")
            if expect_response and not raw.strip():
                return {"jsonrpc": "2.0", "id": request_id, "result": {"status": "accepted"}}

        if not expect_response:
            return {}
        # Streamable HTTP can return SSE frames.
        if raw.lstrip().startswith("{"):
            parsed = json.loads(raw)
            if request_id is None or parsed.get("id") == request_id:
                return parsed
            raise ValueError(f"Unexpected MCP response id: {parsed.get('id')}")

        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                payload = json.loads(line[len("data:"):].strip())
                if request_id is None or payload.get("id") == request_id:
                    return payload
        raise ValueError(f"Invalid MCP HTTP response: {raw[:200]}")

    def _read_headers(self, stream, deadline: float) -> str:
        data = b""
        while b"\r\n\r\n" not in data and b"\n\n" not in data:
            data += self._read_exact(stream.fileno(), 1, deadline)
        if b"\r\n\r\n" in data:
            raw = data.split(b"\r\n\r\n", 1)[0]
        else:
            raw = data.split(b"\n\n", 1)[0]
        return raw.decode("utf-8", errors="replace")

    def _read_exact(self, fd: int, n: int, deadline: float) -> bytes:
        chunks = b""
        while len(chunks) < n:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("MCP request timed out")
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                raise TimeoutError("MCP request timed out")
            chunk = os.read(fd, n - len(chunks))
            if not chunk:
                raise ValueError("MCP server closed the connection")
            chunks += chunk
        return chunks

    def _prepare_managed_http_endpoint(self) -> None:
        """Ensure managed HTTP MCP command has a usable port and url."""
        # Always pick an available local port for managed http to avoid collisions.
        port = self._pick_free_port()

        if "--port" in self.args:
            idx = self.args.index("--port")
            if idx + 1 < len(self.args):
                self.args[idx + 1] = str(port)
            else:
                self.args.append(str(port))
        else:
            self.args.extend(["--port", str(port)])

        if self.url:
            parsed = urlparse(self.url)
            host = parsed.hostname or "localhost"
            path = parsed.path or "/mcp"
            self.url = f"http://{host}:{port}{path}"
        else:
            self.url = f"http://localhost:{port}/mcp"

    @staticmethod
    def _pick_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])
