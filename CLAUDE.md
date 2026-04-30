# CLAUDE.md

> **Project**: m-claude-view — ReAct Agent 智能体框架 + 实时可观测 Web Dashboard

---

## 必读文档（每次开始工作前）

1. `AGENTS.md` — 项目结构、代码规范、工具开发规范
2. `PROGRESS.md` — 项目进度追踪
3. `openspec/` — 架构变更提案（OpenSpec 工作流）

---

## 自动进度更新（必须遵守）

每次完成开发任务并提交代码后，**必须自动更新以下文件**，无需用户提醒：

1. **`PROGRESS.md`** — 在 "Recently Completed" 部分添加完成记录
2. **`sprints/active/{日期}/tasks-{gitid}.md`** — 将对应任务状态从 ⬜ 改为 ✅

> GitID 从 `git config user.name` 派生：去空格 → 全小写。例：`丁昂` → `丁昂`
> 这是查看进度的主入口，遗漏更新 = 工作不可见。

---

## 文档同步（必须遵守）

> **核心原则**：代码实现、需求文档（PRD）、详设文档（SPEC）三者始终同步。任何变更有留痕。
> **文档格式**：正文只保留当前态，历史变更外置到 `.changelog.md`。
> 详见：`.claude/skills/doc-sync-after-dev/SKILL.md`

### 增量同步（自动触发）

**Claude 完成一轮代码实现后，必须自查本轮变更是否偏离了需求文档或详设文档。偏离则告知用户并询问是否现在同步。**

自查触发条件（任一成立即需检查）：
1. 本轮对话中用户做了决策（改字段/加功能/不做了/换方案/需求变了）
2. 本轮 Claude 实现了代码变更（涉及接口、数据模型、功能逻辑、组件结构）
3. Claude 在实现过程中发现代码与文档描述不一致

### 全量同步（合并前自动触发）

用户说"准备合并"/"提 PR"/"合并到 master" 时，自动执行 `/doc-sync-after-dev`。

---

## 技术红线（绝对禁止）

### 架构边界

- ❌ `domain/` 层依赖 `infrastructure/` 或 `interfaces/`（依赖方向必须：`interfaces → application → domain ← infrastructure`）
- ❌ 直接在 `domain/` 里引入外部库（LLM SDK、HTTP 框架等）
- ❌ 绕过 `ToolRegistry` 直接实例化或调用工具

### 编码

- ❌ API Key 写入代码或配置文件（必须通过环境变量注入）
- ❌ 空的 catch 块
- ❌ 删除失败的测试来"通过"测试
- ❌ 提交 `.env`、API Key、大文件

### 流程

- ❌ 不 pull 直接 push
- ❌ `git push --force`

---

## 整体架构

```
frontend/ (纯静态 HTML/CSS/JS)
    ↓ REST/HTTP
backend/src/
├── interfaces/           # 入口适配器
│   ├── http/             #   FastAPI REST API (port 8765)
│   └── cli/              #   交互式 REPL
├── application/          # 用例编排、任务服务
│   ├── use_cases/
│   └── services/
├── domain/agent/         # 核心引擎（ReAct 循环、模型、Prompt）
├── infrastructure/       # 外部依赖
│   ├── llm/              #   OpenAI 兼容 LLM 客户端
│   ├── tools/            #   工具体系（base + registry + factory + MCP）
│   │   └── builtin/      #     内置工具（bash, read_file, load_mcp_tools）
│   ├── config/           #   YAML + 环境变量配置
│   └── storage/          #   JSONL 事件日志
└── bootstrap/            # 依赖装配 + 启动自报
```

> **依赖方向**：`interfaces → application → domain ← infrastructure`，domain 层不依赖外部。

---

## 必须遵守

- ✅ Python ≥ 3.10，类型注解必须
- ✅ 依赖管理：`backend/requirements.txt`
- ✅ 新工具放 `backend/src/infrastructure/tools/builtin/`，继承 `Tool` 基类即自动注册
- ✅ MCP 工具只需在 `config.yaml` 的 `mcp.servers` 配置
- ✅ 测试框架：`pytest`，覆盖成功和失败路径
- ✅ 开工前跑 Checklist（见 AGENTS.md）

---

## 常用命令

```bash
# 安装依赖
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 运行测试
PYTHONPATH=backend pytest backend/tests/ -v

# 运行单个测试
PYTHONPATH=backend pytest backend/tests/test_react_engine.py -v

# 启动 Web 服务 (port 8765)
./start.sh

# CLI 模式
PYTHONPATH=backend python -m src.interfaces.cli.main
```

---

## API 端点速查

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web Dashboard |
| `/api/ask` | POST | 提交问题 |
| `/api/runs?limit=500` | GET | 按迭代分组的事件 |
| `/api/packets?limit=400` | GET | 原始事件列表 |
| `/api/groups?limit=400` | GET | 按问题分组 |
| `/api/tasks/{task_id}` | GET | 异步任务状态 |
| `/api/upload` | POST | 文件上传 |
| `/api/files` | GET | 已上传文件列表 |
| `/api/clear` | POST | 清除日志/任务/会话 |

---

## 质量门（提交前必须通过）

| 检查 | 命令 |
|------|------|
| 测试 | `PYTHONPATH=backend pytest backend/tests/ -v` |
| 类型检查 | `pyright` (配置见 `pyrightconfig.json`) |

---

## Commit Message 规范

### GitHub 项目（默认）

使用 Conventional Commits：`feat:` / `fix:` / `refactor:` / `chore:` / `test:` / `docs:`

### GitLab 推送（如需推送到公司 GitLab）

使用中文前缀：`更新:` `修复:` `增加:` `删除:` `临时:` `测试:` `恢复:` `合并:`

---

## Sprint 管理（Wave 模式）

- Sprint 目录：`sprints/active/YYYY-MM-DD/`
- 每波需求一个 Wave 目录：`wave{N}-{timestamp}/`
- 每人独立任务文件：`tasks-{gitid}.md`（只编辑自己的）
- 跨人协调：日期级 `coordination.md`（append-only）

详见：`.claude/skills/sprint-management/SKILL.md`

---

## 项目 Skills（`/` 命令）

| 命令 | 用途 |
|------|------|
| `/sprint-management` | Sprint/Wave 创建与任务管理 |
| `/prd-status` | PRD 版本追踪与 AC 进度聚合 |
| `/doc-sync` | 增量文档同步（开发中随时调用） |
| `/doc-sync-after-dev` | 全量文档同步（合并前执行） |
| `/need-to-code` | 需求 ↔ 文档 ↔ 代码全链路定位 |
| `/spec-prelaunch-review` | 详设开工前全链路代码核验 |
| `/git-workflow` | Git 分支与协作工作流 |
| `/gitlab-auto-commit` | GitLab 自动提交配置 |

---

## OpenSpec 工作流

架构和行为变更使用 OpenSpec 流程管理：

```
openspec/
├── specs/                    ← 已接受的基线 spec
└── changes/<change-id>/      ← 变更提案
    ├── proposal.md           ← Why/What
    ├── tasks.md              ← 实现 checklist
    └── specs/<capability>/
        └── spec.md           ← Spec 增量（ADDED/CHANGED/REMOVED）
```

变更进入 review-ready 状态的条件：`proposal.md` 完整 + `tasks.md` 可执行 + 至少一个 spec delta。
