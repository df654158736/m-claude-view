"""Bash tool for executing shell commands."""
import subprocess
from src.tools.base import Tool


class BashTool(Tool):
    """Tool for executing bash commands."""

    name = "bash"
    description = "在终端执行 Bash 命令，返回命令输出或错误"
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的命令"
            },
            "timeout": {
                "type": "number",
                "description": "超时时间（秒），默认 30",
                "default": 30
            }
        },
        "required": ["command"]
    }

    def execute(self, command: str, timeout: int = 30) -> str:
        """Execute a bash command."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            # 同时显示 stdout 和 stderr
            output = result.stdout
            if result.stderr:
                output += f"\nStderr:\n{result.stderr}"
            return f"Exit code: {result.returncode}\nOutput:\n{output}"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except (OSError, ValueError) as e:
            return f"Error: {str(e)}"