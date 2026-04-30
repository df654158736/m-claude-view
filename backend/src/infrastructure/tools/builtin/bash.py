"""Bash tool for executing shell commands."""
import subprocess

from pydantic import BaseModel, Field

from src.infrastructure.tools.base import Tool


class BashTool(Tool):
    """Tool for executing bash commands."""

    name = "bash"
    description = "在终端执行 Bash 命令，返回命令输出或错误"

    class Input(BaseModel):
        command: str = Field(description="要执行的命令")
        timeout: int = Field(default=30, description="超时时间（秒），默认 30")

    def execute(self, args: Input) -> str:
        if not args.command:
            return "Error: 'command' is required"

        try:
            result = subprocess.run(
                args.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=args.timeout,
            )
            output = result.stdout
            if result.stderr:
                output += f"\nStderr:\n{result.stderr}"
            return f"Exit code: {result.returncode}\nOutput:\n{output}"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {args.timeout} seconds"
        except (OSError, ValueError) as err:
            return f"Error: {str(err)}"
