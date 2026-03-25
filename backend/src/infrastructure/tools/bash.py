"""Bash tool for executing shell commands."""
import subprocess
from typing import Any

from src.infrastructure.tools.base import Tool


class BashTool(Tool):
    """Tool for executing bash commands."""

    name = "bash"
    description = "在终端执行 Bash 命令，返回命令输出或错误"
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的命令",
            },
            "timeout": {
                "type": "number",
                "description": "超时时间（秒），默认 30",
                "default": 30,
            },
        },
        "required": ["command"],
    }

    def execute(self, **kwargs: Any) -> str:
        """Execute a bash command."""
        command = str(kwargs.get("command", ""))
        timeout = kwargs.get("timeout", 30)
        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            timeout = 30
        if not command:
            return "Error: 'command' is required"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\nStderr:\n{result.stderr}"
            return f"Exit code: {result.returncode}\nOutput:\n{output}"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except (OSError, ValueError) as err:
            return f"Error: {str(err)}"
