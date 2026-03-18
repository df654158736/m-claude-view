# ReAct Agent 设计文档

**日期**: 2026-03-18
**目标**: 实现一个类似 Claude Code 的 ReAct Agent，可以边思考边与模型交互、调用工具、不断思考并获取结果最终解决问题

---

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                      CLI (入口)                         │
│                  input → loop → output                  │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    ReActEngine                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │           ReAct Loop (最大 N 轮)                 │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────────┐     │   │
│  │  │ Think   │→ │ Act     │→ │ Observe     │     │   │
│  │  │ 模型决策 │  │ 调用工具 │  │ 解析结果+反思│     │   │
│  │  └─────────┘  └─────────┘  └─────────────┘     │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    ToolManager                          │
│         注册工具 → 执行工具 → 返回结果                    │
│   ┌──────────────┐  ┌──────────────────────────┐       │
│   │ BashTool     │  │ MCPClient (Playwright)   │       │
│   └──────────────┘  └──────────────────────────┘       │
└──────────────────────────┬──────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────┐
│               LLMClient (DashScope)                    │
│           OpenAI 兼容 API 调用                           │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 核心模块

| 模块 | 职责 |
|------|------|
| `CLI` | 交互式命令行，任务输入，结果展示 |
| `ReActEngine` | ReAct 循环控制，思考-行动-观察 |
| `ToolManager` | 工具注册、发现、执行 |
| `LLMClient` | 与 DashScope API 交互 |
| `Config` | 配置文件管理 |

---

## 3. ReAct 流程

```
1. 用户输入任务
2. while 未完成 and 未达最大轮数:
   a. Think: 发送历史消息给模型，让它决定：
      - 继续思考/分析
      - 调用工具（附上工具描述）
      - 完成任务
   b. if 模型选择调用工具:
      - 解析工具名和参数
      - ToolManager 执行工具
      - 将结果加入消息历史
   c. if 模型选择完成任务:
      - 返回最终结果，退出循环
3. 达到最大轮数仍未完成，返回失败
```

---

## 4. 配置文件结构

```yaml
# config.yaml
llm:
  api_key: "sk-xxx"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen-max"
  max_iterations: 20  # 最大循环轮数

display:
  thinking_collapsed: true  # 折叠式展示思考过程
  verbose: true             # 详细日志

tools:
  - name: bash
    enabled: true
    description: "执行 Bash 命令"

  - name: playwright
    enabled: true
    command: "npx playwright"  # 或自定义 MCP 命令
    description: "浏览器自动化工具"
```

---

## 5. 工具系统设计

### 5.1 工具注册机制

```python
# tools/base.py
class Tool(ABC):
    name: str           # 工具名，供模型识别
    description: str   # 工具描述，给模型看
    parameters: dict   # JSON Schema 格式的参数定义

    @abstractmethod
    def execute(self, **kwargs) -> str:
        pass
```

### 5.2 工具发现与执行

```python
# tools/registry.py
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool_schema(self) -> list[dict]:
        """生成给模型的工具描述"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict) -> str:
        return self._tools[name].execute(**arguments)
```

### 5.3 内置工具：BashTool

```python
# tools/bash.py
class BashTool(Tool):
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
        result = subprocess.run(
            command, shell=True,
            capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout or result.stderr
        return f"Exit code: {result.returncode}\nOutput:\n{output}"
```

### 5.4 MCP 工具配置

通过配置文件指定 MCP 服务器：

```yaml
# config.yaml
mcp:
  # 方式 1：使用 npx 运行 MCP
  servers:
    playwright:
      command: "npx"
      args: ["-y", "@anthropic/playwright-mcp"]
      env: {}  # 可选环境变量

    # 可添加更多 MCP 服务器
    # my其他_mcp:
    #   command: "node"
    #   args: ["/path/to/mcp-server.js"]
```

MCP 工具将通过 `mcp` 库连接，获取可用工具列表并注册到 ToolRegistry。

**注意**: Playwright MCP 需要本地 Node.js 环境运行。

---

## 6. 消息格式设计

### 6.1 与模型交互的消息结构

```python
from typing import Literal

Message = dict  # OpenAI 兼容格式

# 系统提示词
system_message = {
    "role": "system",
    "content": """你是一个 ReAct Agent。

## 工作流程
1. 思考当前任务状态
2. 如需执行操作，使用工具
3. 根据工具返回结果决定下一步
4. 完成任务后返回最终结果

## 规则
- 仔细分析工具返回的结果
- 如果结果不理想，反思原因并重试
- 只在确实完成目标后返回最终答案"""
}

# 用户任务
user_message = {
    "role": "user",
    "content": "帮我写一个 hello.py 并执行它"
}
```

### 6.2 工具调用消息

模型返回的工具调用（assistant 消息）：

```python
tool_call_message = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": '{"command": "echo hello > hello.py"}'
            }
        }
    ]
}
```

工具执行结果（tool 消息）：

```python
tool_result_message = {
    "role": "tool",
    "tool_call_id": "call_123",
    "content": "Exit code: 0\nOutput:\n"  # BashTool 的返回
}
```

### 6.3 ReAct 循环中的消息历史

```python
messages = [
    system_message,
    user_message,
    # 第一轮
    {"role": "assistant", "content": "我需要先创建文件..."},
    {"role": "tool", "tool_call_id": "call_1", "content": "文件已创建"},
    # 第二轮
    {"role": "assistant", "content": "现在执行文件..."},
    {"role": "tool", "tool_call_id": "call_2", "content": "Hello, World!"},
    # 第三轮
    {"role": "assistant", "content": "任务完成！最终结果..."}
]
```

### 6.4 模型输出解析

```python
# llm_client.py
def parse_response(response) -> tuple[str, list[ToolCall] | None]:
    """解析模型返回，决定下一步动作"""

    # 情况 1：返回最终答案
    if response.stop_reason == "end_turn":
        return response.content, None

    # 情况 2：调用工具
    if response.tool_calls:
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments)
            )
            for tc in response.tool_calls
        ]
        return None, tool_calls

    # 情况 3：其他停止原因（如 max_tokens）
    return response.content, None
```

---

## 7. 错误处理与日志设计

### 7.1 日志级别

```python
# logging_config.py
import logging

LOG_LEVELS = {
    "quiet":      # 只显示最终结果
    "normal":     # 显示关键节点（轮次、工具调用、结果）
    "verbose":    # 显示完整思考过程（ReAct每轮详情）
    "debug":      # 调试信息（API 请求/响应、异常详情）
}

# 默认 verbose
logger = logging.getLogger("react_agent")
```

### 7.2 日志输出示例

**verbose 模式：**
```
══════════════════════════════════════════════════
🧠 第 1 轮思考
══════════════════════════════════════════════════
[折叠] 思考过程：分析任务，需要先检查当前目录...

────────────────────────────────────────────────
⚡ 工具调用: bash
────────────────────────────────────────────────
命令: ls -la

────────────────────────────────────────────────
📋 工具返回:
────────────────────────────────────────────────
Exit code: 0
Output:
total 8
drwxr-xr 2 user user 4096 Mar 18 10:21 .
...

────────────────────────────────────────────────
🔄 反思: 已确认目录为空，可以继续创建文件...
══════════════════════════════════════════════════
```

### 7.3 错误处理策略

| 错误类型 | 处理方式 |
|---------|---------|
| API 调用失败 | 重试 3 次，指数退避 |
| 工具执行失败 | 返回错误信息给模型，让模型决定如何处理 |
| 工具超时 | 终止工具执行，返回超时错误 |
| 解析错误 | 记录日志，尝试恢复 |
| 达到最大轮数 | 返回失败，列出已执行的步骤 |

```python
# react_engine.py
MAX_RETRIES = 3

async def call_llm_with_retry(self, messages):
    for attempt in range(MAX_RETRIES):
        try:
            return await self.llm_client.chat(messages)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 2 ** attempt  # 指数退避
            logger.warning(f"API 调用失败，{wait}秒后重试: {e}")
            await asyncio.sleep(wait)
```

---

## 8. 文件结构

```
react-agent/
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖
├── src/
│   ├── __init__.py
│   ├── cli.py           # 入口，REPL 循环
│   ├── config.py        # 配置加载
│   ├── react_engine.py  # ReAct 核心逻辑
│   ├── llm_client.py    # LLM API 调用
│   └── tools/
│       ├── __init__.py
│       ├── base.py      # Tool 基类
│       ├── registry.py  # 工具注册表
│       ├── bash.py      # BashTool
│       └── mcp.py       # MCP 客户端
├── docs/
│   └── plans/           # 设计文档
└── main.py              # 入口文件
```

---

## 9. 完整配置示例

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
  log_level: "verbose"  # quiet/normal/verbose/debug

tools:
  - name: bash
    enabled: true
    timeout: 30

mcp:
  servers:
    playwright:
      command: "npx"
      args: ["-y", "@anthropic/playwright-mcp"]
```

---

## 10. MCP 服务器配置说明

### 10.1 Playwright MCP

需要本地安装 Node.js，然后配置：

```yaml
mcp:
  servers:
    playwright:
      command: "npx"
      args: ["-y", "@anthropic/playwright-mcp"]
```

Agent 启动时会自动通过 `npx` 拉起 MCP 服务器进程。

### 10.2 添加其他 MCP 服务器

```yaml
mcp:
  servers:
    # 示例：其他 MCP 服务器
    filesystem:
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]

    custom:
      command: "node"
      args: ["/absolute/path/to/your/mcp-server.js"]
```