# MClaude ReAct Agent

一个面向工程化落地的 ReAct Agent 项目，支持：
- 多轮推理 + 工具调用（Bash / MCP）
- FastAPI Web 服务与前端可观测面板
- 结构化事件日志（JSON / 可读格式 / JSONL 落盘）

项目目标不是“只跑通一次”，而是保持可维护、可观测、可扩展。

## 核心特性

- ReAct 主循环：模型推理、工具执行、结果回填、迭代收敛。
- 工具体系：统一 `Tool` 抽象 + 注册表 + 工厂装配。
- Web 控制台：查看问题轮次、事件时间线、JSON 详情，支持提交问题与清空历史。
- 会话与任务分离：引擎会话历史与异步任务状态独立管理。
- 配置与密钥分离：模型参数通过环境变量驱动（`.env`）。

## 技术栈

- Python 3.10+
- OpenAI Compatible SDK (`openai`)
- FastAPI + Uvicorn
- PyYAML
- pytest

## 项目结构

```text
.
├─ backend/
│  ├─ config.yaml
│  ├─ requirements.txt
│  ├─ src/
│  │  ├─ main.py                         # 顶层 HTTP 启动入口
│  │  ├─ domain/                         # 领域层（核心业务）
│  │  │  └─ agent/
│  │  │     ├─ engine.py                 # ReAct 核心流程
│  │  │     ├─ packet_logger.py          # 结构化日志能力
│  │  │     ├─ prompt_templates.py       # Prompt 模板
│  │  │     └─ models.py
│  │  ├─ application/                    # 应用层（编排）
│  │  │  ├─ services/agent_task_service.py
│  │  │  └─ use_cases/run_agent.py
│  │  ├─ infrastructure/                 # 基础设施层（外部依赖）
│  │  │  ├─ config/settings.py
│  │  │  ├─ llm/openai_client.py
│  │  │  ├─ storage/packet_log_repo.py
│  │  │  └─ tools/{base,registry,bash,mcp_server,factory}.py
│  │  ├─ interfaces/                     # 接口层（适配器）
│  │  │  ├─ http/main.py
│  │  │  └─ cli/main.py
│  │  └─ bootstrap/container.py          # 依赖装配
│  └─ tests/
├─ frontend/                              # 静态前端
├─ logs/
├─ start.sh
├─ .env.example
└─ openspec/
```

## 架构说明（简版）

- `domain`：只负责核心规则与流程，不直接依赖 HTTP/CLI。
- `application`：组织用例流程与任务服务。
- `infrastructure`：封装 LLM、工具、存储、配置等外部系统。
- `interfaces`：提供 CLI/FastAPI 入口，将外部输入映射到应用层。
- `bootstrap`：统一进行依赖注入与装配。

这种分层方式能降低耦合，避免“入口层逻辑反向污染核心流程”。

## 快速开始

### 1) 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2) 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填好：

```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max
LLM_MAX_ITERATIONS=20
LLM_TEMPERATURE=0.7
```

说明：
- `LLM_API_KEY` 必填。
- 其余字段可省略，`start.sh` 会提供默认值。

### 3) 启动服务

```bash
./start.sh
```

默认地址：
- http://127.0.0.1:8765
- 局域网访问：`start.sh` 使用 `0.0.0.0:8765`

## CLI 模式

```bash
PYTHONPATH=backend python -m src.interfaces.cli.main
```

适合调试引擎行为与工具调用，不依赖前端。

## 测试

```bash
PYTHONPATH=backend pytest -q backend/tests
```

当前测试覆盖：
- engine 主流程
- 工具注册与执行
- MCP 工具行为（stdio/http）
- 日志读取与分组
- 任务服务提交/清理行为

## API 概览

- `GET /`：前端主页
- `GET /api/runs?limit=...`：按轮次返回事件
- `GET /api/packets?limit=...`：原始 packet 列表
- `GET /api/groups?limit=...&merge_same_question=true`：按问题分组
- `POST /api/ask`：提交问题
- `GET /api/tasks/{task_id}`：查询异步任务状态
- `POST /api/clear`：清空日志与任务状态并重置会话

## 日志与可观测性

日志行为由 `backend/config.yaml` 的 `display` 段控制：
- `packet_log_mode`: `json` / `readable` / `both`
- `json_pretty`: 是否美化 JSON
- `packet_log_file`: JSONL 落盘路径（默认 `logs/packets.jsonl`）

## 常见问题

### 1) 新开终端看不到 `LLM_API_KEY`

这是正常的：`.env` 是在 `start.sh` 运行时加载，不会自动注入所有 shell 会话。

### 2) `ModuleNotFoundError: fastapi` / `openai`

先激活虚拟环境并安装依赖：

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 3) 点击“清空历史”后模型仍记得旧上下文

已修复：`/api/clear` 会调用引擎 `reset_session()`，清空会话历史。

## 安全建议

- 不要把真实 API Key 提交到仓库。
- `.env` 已被 `.gitignore` 忽略，请仅在本地保存。
- Bash 工具有执行风险，生产环境建议加白名单策略与审批机制。

## 变更管理

本仓库使用 OpenSpec 风格管理架构变更：
- `openspec/changes/*`：变更 proposal/tasks/spec
- `openspec/specs/*`：稳定规范

## 许可证

当前仓库未单独声明 LICENSE。若用于团队协作，建议尽快补充。
