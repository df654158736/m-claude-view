# MClaude ReAct Agent

基于 ReAct（Reasoning + Acting）范式的智能体框架，配套实时可观测 Web 面板。

支持任意 OpenAI 兼容 LLM、内置工具与 MCP 协议工具扩展、结构化事件追踪，开箱即用。

## 核心能力

**智能体引擎**
- ReAct 循环：推理 → 工具调用 → 观察 → 迭代收敛
- 多轮会话历史，支持跨 run 上下文保持
- 可配置最大迭代次数、温度等参数

**工具体系**
- Pydantic 声明式工具参数，自动生成 JSON Schema
- 自动发现注册：新建文件即可添加工具，零配置
- MCP 工具懒加载：启动时发现 → 按需激活 → 自动注入 schema
- 内置工具：`bash`（Shell 执行）、`read_file`（文本/PDF 读取）、`load_mcp_tools`（MCP 工具加载器）

**可观测面板**
- 三栏布局：问题轮次 → 事件时间线 → JSON 结构化详情
- 实时轮询，支持暂停/恢复
- 文件上传，自动注入到 Agent 上下文
- MCP 截图（base64 图片）直接渲染

**双入口**
- Web 服务（FastAPI）：面板 + REST API
- CLI REPL：终端交互，适合调试

## 架构

```
backend/src/
├── domain/agent/            # 核心：ReAct 引擎、模型、Prompt、日志
├── application/             # 编排：任务服务、用例
├── infrastructure/          # 外部依赖
│   ├── llm/                 #   LLM 客户端（OpenAI 兼容）
│   ├── tools/               #   工具抽象 + 注册表 + MCP 适配
│   │   ├── base.py          #     Tool 基类（Pydantic + 自动注册）
│   │   ├── registry.py      #     注册表（执行、延迟加载目录）
│   │   ├── mcp_server.py    #     MCP 协议适配（stdio / HTTP）
│   │   ├── mcp_sub_tool.py  #     MCP 子工具代理
│   │   └── builtin/         #     内置工具（bash, read_file, load_mcp_tools）
│   ├── config/              #   配置加载（YAML + 环境变量）
│   └── storage/             #   事件日志读写
├── interfaces/              # 入口适配
│   ├── http/                #   FastAPI 路由
│   └── cli/                 #   交互式 REPL
└── bootstrap/               # 依赖装配 + 启动自报

frontend/                    # 纯静态前端（HTML + CSS + JS，无构建）
```

分层规则：依赖单向向下，domain 不依赖 infrastructure，interfaces 不包含业务逻辑。

## 快速开始

```bash
# 1. 安装依赖
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. 配置
cp .env.example .env
# 编辑 .env，填写 LLM_API_KEY（必填）

# 3. 启动
./start.sh
# 访问 http://localhost:8765
```

### 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `LLM_API_KEY` | 是 | - | LLM API 密钥 |
| `LLM_BASE_URL` | 否 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | API 地址 |
| `LLM_MODEL` | 否 | `qwen-max` | 模型名称 |
| `LLM_MAX_ITERATIONS` | 否 | `20` | 最大迭代轮数 |
| `LLM_TEMPERATURE` | 否 | `0.7` | 采样温度 |
| `PORT` | 否 | `8765` | 服务端口 |

### CLI 模式

```bash
PYTHONPATH=backend python -m src.interfaces.cli.main
```

## 添加工具

在 `backend/src/infrastructure/tools/builtin/` 下新建文件即可：

```python
from pydantic import BaseModel, Field
from src.infrastructure.tools.base import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "工具描述"

    class Input(BaseModel):
        query: str = Field(description="查询内容")

    def execute(self, args: Input) -> str:
        return f"结果: {args.query}"
```

在 `config.yaml` 的 `tools` 列表中启用：

```yaml
tools:
  - name: my_tool
    enabled: true
```

无需修改注册逻辑，框架通过 `__init_subclass__` 自动发现。

## 添加 MCP 服务

在 `config.yaml` 的 `mcp.servers` 中配置：

```yaml
mcp:
  servers:
    # HTTP 远程服务
    amap-maps:
      type: "http"
      url: "https://mcp.amap.com/mcp?key=YOUR_KEY"

    # 本地 stdio 进程（自动管理生命周期）
    playwright:
      type: "http"
      command: "npx"
      args: ["-y", "@playwright/mcp@latest", "--headless"]
      url: "http://localhost/mcp"
      ready_timeout: 120
```

启动时自动发现所有子工具并注册到延迟加载目录。Agent 通过 `load_mcp_tools` 按需加载 schema 后调用；即使跳过加载步骤，直接调用也会自动激活。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | Web 面板 |
| `POST` | `/api/ask` | 提交问题（自动注入已上传文件路径） |
| `GET` | `/api/runs?limit=500` | 按轮次返回事件 |
| `GET` | `/api/packets?limit=400` | 原始事件列表 |
| `GET` | `/api/groups?limit=400` | 按问题分组 |
| `GET` | `/api/tasks/{task_id}` | 查询异步任务状态 |
| `POST` | `/api/upload` | 上传文件（multipart/form-data） |
| `GET` | `/api/files` | 列出已上传文件 |
| `POST` | `/api/clear` | 清空日志、任务、会话 |

## 日志与可观测

事件以 JSONL 格式落盘到 `logs/packets.jsonl`，每条记录包含：

- `type`：`user` / `llm_request` / `llm_response` / `tool` / `agent`
- `iteration`：当前迭代轮次
- 完整的请求/响应/工具调用数据

通过 `config.yaml` 的 `display` 段控制输出行为：

```yaml
display:
  packet_log_mode: "both"    # json / readable / both
  packet_log_file: "logs/packets.jsonl"
  json_pretty: true
```

## 测试

```bash
PYTHONPATH=backend pytest backend/tests/ -v
```

覆盖范围：ReAct 引擎主循环、工具注册与执行、MCP 协议适配（stdio/HTTP）、日志读写与分组、HTTP API、任务服务。

## 技术栈

- **语言**：Python 3.10+
- **Web**：FastAPI + Uvicorn
- **LLM**：OpenAI Compatible SDK
- **工具参数**：Pydantic v2
- **PDF 解析**：PyMuPDF
- **前端**：原生 HTML/CSS/JS（无构建工具）
- **测试**：pytest
