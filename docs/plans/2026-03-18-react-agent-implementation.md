# ReAct Agent 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现一个类似 Claude Code 的 ReAct Agent，可以边思考边与模型交互、调用工具、不断思考并获取结果最终解决问题

**Architecture:** 基于 ReAct (Reasoning + Acting) 模式，通过思考-行动-观察的循环让模型自主决定何时调用工具、如何迭代。工具系统支持内置工具和 MCP 扩展

**Tech Stack:** Python, OpenAI SDK (DashScope 兼容), MCP (Model Context Protocol)

---

## Task 1: 项目结构搭建

**Files:**
- Create: `config.yaml`
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/cli.py`
- Create: `src/config.py`

**Step 1: Create project directories**

```bash
mkdir -p src/tools
mkdir -p tests
```

**Step 2: Create config.yaml**

```yaml
# config.yaml
llm:
  api_key: "sk-3d8302efddc24a9494d1858d8d5ec0f8"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen-max"
  max_iterations: 20
  temperature: 0.7

display:
  thinking_collapsed: true
  log_level: "verbose"

tools:
  - name: bash
    enabled: true
    timeout: 30

mcp:
  servers: {}
```

**Step 3: Create requirements.txt**

```
openai>=1.0.0
pyyaml>=6.0
```

**Step 4: Create src/__init__.py**

```python
"""ReAct Agent - A self-thinking agent that uses tools."""
__version__ = "0.1.0"
```

**Step 5: Create src/config.py**

```python
"""Configuration loading module."""
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    max_iterations: int = 20
    temperature: float = 0.7


@dataclass
class DisplayConfig:
    thinking_collapsed: bool = True
    log_level: str = "verbose"


@dataclass
class ToolConfig:
    name: str
    enabled: bool = True
    timeout: int = 30
    command: Optional[str] = None
    args: Optional[list] = None


@dataclass
class MCPServerConfig:
    command: str
    args: list = None
    env: dict = None


@dataclass
class Config:
    llm: LLMConfig
    display: DisplayConfig
    tools: list[ToolConfig]
    mcp: dict


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return Config(
        llm=LLMConfig(**data.get("llm", {})),
        display=DisplayConfig(**data.get("display", {})),
        tools=[ToolConfig(**t) for t in data.get("tools", [])],
        mcp=data.get("mcp", {}).get("servers", {})
    )
```

**Step 6: Create src/cli.py (stub)**

```python
"""CLI entry point."""
from src.config import load_config


def main():
    config = load_config()
    print("ReAct Agent initialized")
    print(f"Model: {config.llm.model}")


if __name__ == "__main__":
    main()
```

**Step 7: Commit**

```bash
git add -A
git commit -m "chore: project structure with config loading"
```

---

## Task 2: LLM 客户端实现

**Files:**
- Create: `src/llm_client.py`
- Create: `tests/test_llm_client.py`

**Step 1: Write the failing test**

```python
# tests/test_llm_client.py
import pytest
from unittest.mock import Mock, patch
from src.llm_client import LLMClient


def test_llm_client_initialization():
    """Test LLM client can be initialized with config."""
    config = Mock()
    config.api_key = "test-key"
    config.base_url = "https://api.example.com"
    config.model = "test-model"
    config.temperature = 0.7

    client = LLMClient(config)
    assert client.model == "test-model"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_llm_client.py::test_llm_client_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src'"

**Step 3: Write minimal implementation**

```python
# src/llm_client.py
"""LLM Client for interacting with DashScope API."""
import json
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI


@dataclass
class ToolCall:
    """Represents a tool call from the model."""
    id: str
    name: str
    arguments: dict


class LLMClient:
    """Client for LLM API interactions."""

    def __init__(self, config):
        self.api_key = config.api_key
        self.base_url = config.base_url
        self.model = config.model
        self.temperature = config.temperature
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def chat(self, messages: list, tools: Optional[list] = None):
        """Send a chat request to the LLM."""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }
        if tools:
            params["tools"] = tools

        response = self.client.chat.completions.create(**params)
        return response.choices[0]

    @staticmethod
    def parse_response(response) -> tuple[Optional[str], list[ToolCall]]:
        """Parse LLM response to extract content or tool calls."""
        message = response.message

        # Check for tool calls
        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments)
                ))
            return None, tool_calls

        # Return content
        return message.content, []
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_llm_client.py::test_llm_client_initialization -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_client.py tests/test_llm_client.py
git commit -m "feat: add LLM client for DashScope API"
```

---

## Task 3: 工具系统基类和注册表

**Files:**
- Create: `src/tools/base.py`
- Create: `src/tools/registry.py`
- Create: `tests/test_tools.py`

**Step 1: Write the failing test**

```python
# tests/test_tools.py
import pytest
from src.tools.base import Tool
from src.tools.registry import ToolRegistry


def test_tool_registry_register():
    """Test tool can be registered."""
    registry = ToolRegistry()

    class MockTool(Tool):
        name = "mock_tool"
        description = "A mock tool"
        parameters = {"type": "object", "properties": {}}

        def execute(self, **kwargs):
            return "executed"

    registry.register(MockTool())
    assert "mock_tool" in registry._tools


def test_tool_registry_get_schema():
    """Test tool schema generation."""
    registry = ToolRegistry()

    class MockTool(Tool):
        name = "mock_tool"
        description = "A mock tool"
        parameters = {"type": "object", "properties": {}}

        def execute(self, **kwargs):
            return "executed"

    registry.register(MockTool())
    schema = registry.get_tool_schema()

    assert len(schema) == 1
    assert schema[0]["function"]["name"] == "mock_tool"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_tools.py -v`
Expected: FAIL with "No module named 'src.tools'"

**Step 3: Write minimal implementation**

```python
# src/tools/__init__.py
"""Tools package."""
```

```python
# src/tools/base.py
"""Base Tool class."""
from abc import ABC, abstractmethod


class Tool(ABC):
    """Base class for all tools."""

    name: str = ""
    description: str = ""
    parameters: dict = {}

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given arguments."""
        pass
```

```python
# src/tools/registry.py
"""Tool registry for managing available tools."""
from typing import Dict, List
from src.tools.base import Tool


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        """Get a tool by name."""
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        return self._tools[name]

    def execute(self, name: str, arguments: dict) -> str:
        """Execute a tool by name with given arguments."""
        tool = self.get_tool(name)
        return tool.execute(**arguments)

    def get_tool_schemas(self) -> List[dict]:
        """Get tool schemas for LLM."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            })
        return schemas
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tools/ tests/test_tools.py
git commit -m "feat: add tool base class and registry"
```

---

## Task 4: BashTool 实现

**Files:**
- Create: `src/tools/bash.py`
- Create: `tests/test_bash_tool.py`

**Step 1: Write the failing test**

```python
# tests/test_bash_tool.py
import pytest
from src.tools.bash import BashTool


def test_bash_tool_execute():
    """Test bash tool can execute commands."""
    tool = BashTool()
    result = tool.execute(command="echo hello")
    assert "hello" in result


def test_bash_tool_name():
    """Test bash tool has correct name."""
    tool = BashTool()
    assert tool.name == "bash"


def test_bash_tool_schema():
    """Test bash tool generates correct schema."""
    tool = BashTool()
    assert "command" in tool.parameters["properties"]
    assert "timeout" in tool.parameters["properties"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_bash_tool.py -v`
Expected: FAIL with "No module named 'src.tools.bash'"

**Step 3: Write minimal implementation**

```python
# src/tools/bash.py
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
            output = result.stdout or result.stderr
            return f"Exit code: {result.returncode}\nOutput:\n{output}"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds"
        except Exception as e:
            return f"Error: {str(e)}"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_bash_tool.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/tools/bash.py tests/test_bash_tool.py
git commit -m "feat: add BashTool for shell command execution"
```

---

## Task 5: ReAct Engine 核心实现

**Files:**
- Create: `src/react_engine.py`
- Create: `tests/test_react_engine.py`

**Step 1: Write the failing test**

```python
# tests/test_react_engine.py
import pytest
from unittest.mock import Mock, MagicMock
from src.react_engine import ReActEngine


def test_react_engine_initialization():
    """Test ReAct engine can be initialized."""
    llm_client = Mock()
    tool_registry = Mock()
    config = Mock()
    config.max_iterations = 10
    config.temperature = 0.7

    engine = ReActEngine(llm_client, tool_registry, config)
    assert engine.max_iterations == 10


def test_react_engine_build_messages():
    """Test message building with system prompt."""
    llm_client = Mock()
    tool_registry = Mock()
    tool_registry.get_tool_schemas.return_value = []

    config = Mock()
    config.max_iterations = 10
    config.temperature = 0.7

    engine = ReActEngine(llm_client, tool_registry, config)
    messages = engine.build_messages("test task")

    assert messages[0]["role"] == "system"
    assert "test task" in messages[1]["content"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_react_engine.py -v`
Expected: FAIL with "No module named 'src.react_engine'"

**Step 3: Write minimal implementation**

```python
# src/react_engine.py
"""ReAct Engine - Core reasoning and action loop."""
import logging
from typing import Optional
from src.llm_client import LLMClient, ToolCall
from src.tools.registry import ToolRegistry


logger = logging.getLogger("react_agent")


class ReActEngine:
    """ReAct (Reasoning + Acting) engine for agent execution."""

    SYSTEM_PROMPT = """你是一个 ReAct Agent。

## 工作流程
1. 思考当前任务状态
2. 如需执行操作，使用工具
3. 根据工具返回结果决定下一步
4. 完成任务后返回最终结果

## 规则
- 仔细分析工具返回的结果
- 如果结果不理想，反思原因并重试
- 只在确实完成目标后返回最终答案
- 如果需要执行shell命令，使用 bash 工具
"""

    def __init__(self, llm_client: LLMClient, tool_registry: ToolRegistry, config):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.max_iterations = config.max_iterations
        self.config = config

        # Message history
        self.messages = []

    def build_messages(self, user_task: str) -> list:
        """Build initial messages with system prompt."""
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": user_task}
        ]
        return messages

    def run(self, task: str) -> str:
        """Run the ReAct loop for a given task."""
        self.messages = self.build_messages(task)

        logger.info(f"Starting ReAct loop for task: {task[:50]}...")

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"--- Iteration {iteration}/{self.max_iterations} ---")

            # Get tool schemas
            tools = self.tool_registry.get_tool_schemas()

            # Call LLM
            response = self.llm_client.chat(self.messages, tools if tools else None)
            content, tool_calls = self.llm_client.parse_response(response)

            # Add assistant message to history
            assistant_msg = {"role": "assistant"}
            if content:
                assistant_msg["content"] = content
            if tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": str(tc.arguments)
                        }
                    }
                    for tc in tool_calls
                ]
            self.messages.append(assistant_msg)

            # If no tool calls, return the final response
            if not tool_calls:
                logger.info(f"Task completed in {iteration} iterations")
                return content or "No response"

            # Execute tool calls
            for tc in tool_calls:
                logger.info(f"Executing tool: {tc.name} with args: {tc.arguments}")
                try:
                    result = self.tool_registry.execute(tc.name, tc.arguments)
                    logger.info(f"Tool result: {result[:200]}...")
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"
                    logger.error(result)

                # Add tool result to history
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })

        # Max iterations reached
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        return "任务未在最大迭代次数内完成"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_react_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/react_engine.py tests/test_react_engine.py
git commit -m "feat: add ReAct engine core logic"
```

---

## Task 6: 完整 CLI 交互界面

**Files:**
- Modify: `src/cli.py`

**Step 1: Update cli.py**

```python
"""CLI entry point for ReAct Agent."""
import sys
import logging
from src.config import load_config
from src.llm_client import LLMClient
from src.tools.registry import ToolRegistry
from src.tools.bash import BashTool
from src.react_engine import ReActEngine


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("react_agent")


def setup_tools(config):
    """Setup tool registry with configured tools."""
    registry = ToolRegistry()

    for tool_config in config.tools:
        if not tool_config.enabled:
            continue

        if tool_config.name == "bash":
            registry.register(BashTool())
            logger.info("Registered bash tool")
        else:
            logger.warning(f"Unknown tool: {tool_config.name}")

    return registry


def main():
    """Main CLI entry point."""
    print("=" * 60)
    print("🤖 ReAct Agent - 自主思考与工具调用")
    print("=" * 60)
    print()

    # Load config
    try:
        config = load_config("config.yaml")
        print(f"✓ 配置加载成功")
        print(f"  Model: {config.llm.model}")
        print(f"  Max iterations: {config.llm.max_iterations}")
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        sys.exit(1)

    # Setup components
    llm_client = LLMClient(config.llm)
    tool_registry = setup_tools(config)
    engine = ReActEngine(llm_client, tool_registry, config.llm)

    print(f"✓ 工具注册完成: {list(tool_registry._tools.keys())}")
    print()
    print("输入任务开始执行，输入 'exit' 或 'quit' 退出")
    print("-" * 60)

    # REPL loop
    while True:
        try:
            task = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if not task:
            continue

        if task.lower() in ("exit", "quit", "q"):
            print("再见!")
            break

        print()
        print("=" * 60)
        print("🚀 开始执行任务...")
        print("=" * 60)

        result = engine.run(task)

        print()
        print("=" * 60)
        print("📋 最终结果:")
        print("=" * 60)
        print(result)


if __name__ == "__main__":
    main()
```

**Step 2: Update config.py to fix llm config access**

```python
# src/config.py - update LLMConfig reference
def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return Config(
        llm=LLMConfig(**data.get("llm", {})),
        display=DisplayConfig(**data.get("display", {})),
        tools=[ToolConfig(**t) for t in data.get("tools", [])],
        mcp=data.get("mcp", {}).get("servers", {})
    )
```

**Step 3: Test the CLI**

Run: `python -m src.cli`
Expected: Shows initialization message, accepts input

**Step 4: Commit**

```bash
git add src/cli.py src/config.py
git commit -m "feat: add complete CLI with REPL loop"
```

---

## Task 7: MCP 客户端支持（可选/基础）

**Files:**
- Create: `src/tools/mcp.py`
- Modify: `src/cli.py` (集成 MCP)

**Step 1: Write MCP client stub**

```python
# src/tools/mcp.py
"""MCP Client for connecting to MCP servers."""
import asyncio
import logging
from typing import Optional
from src.tools.base import Tool


logger = logging.getLogger("react_agent")


class MCPTool(Tool):
    """Wrapper for MCP server tools."""

    def __init__(self, name: str, description: str, parameters: dict, mcp_client):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.mcp_client = mcp_client

    def execute(self, **kwargs) -> str:
        """Execute via MCP client."""
        # This is a stub - full MCP implementation would go here
        return f"MCP tool {self.name} called with {kwargs}"


class MCPClient:
    """Client for connecting to MCP servers."""

    def __init__(self, command: str, args: list = None, env: dict = None):
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process = None

    def start(self):
        """Start the MCP server process."""
        # Stub - would start the MCP server
        logger.info(f"Starting MCP server: {self.command} {' '.join(self.args)}")

    def stop(self):
        """Stop the MCP server process."""
        # Stub
        pass

    def list_tools(self) -> list:
        """List available tools from MCP server."""
        # Stub
        return []


def create_mcp_tools(config: dict) -> list[Tool]:
    """Create tools from MCP configuration."""
    tools = []
    for name, server_config in config.items():
        client = MCPClient(
            command=server_config.get("command"),
            args=server_config.get("args", []),
            env=server_config.get("env", {})
        )
        # Start client (stub)
        client.start()
        logger.info(f"Connected to MCP server: {name}")
    return tools
```

**Step 2: Integrate MCP into cli.py**

```python
# In cli.py, add after tool setup:
# if config.mcp:
#     from src.tools.mcp import create_mcp_tools
#     mcp_tools = create_mcp_tools(config.mcp)
#     for tool in mcp_tools:
#         tool_registry.register(tool)
```

**Step 3: Commit**

```bash
git add src/tools/mcp.py
git commit -m "feat: add MCP client stub"
```

---

## 执行方式

**Plan complete and saved to `docs/plans/2026-03-18-react-agent-implementation.md`. Two execution options:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?