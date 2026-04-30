# m-claude-view 统一注释规范

> **版本**: 1.0
> **生效日期**: 2026-03-31
> **适用范围**: Python / TypeScript / HTML（静态前端）

---

## 1. 总则

### 1.1 注释语言

| 场景 | 语言 | 示例 |
|------|------|------|
| 领域/业务概念 | **中文** | `"""ReAct 循环引擎 — 执行 Thought/Action/Observation 循环"""` |
| 通用技术概念 | **英文** | `"""Thread-safe LRU cache with TTL eviction"""` |
| API 文档（OpenAPI） | **英文** | FastAPI `summary` / `description` |
| TODO / FIXME | **中文** | `# TODO: 迁移到真实 API 后删除 mock 逻辑` |

> **原则**: 优先中文以降低团队沟通成本；对外暴露的 API 文档使用英文。

### 1.2 什么必须注释

| 级别 | 必须注释 | 可选 |
|------|---------|------|
| **模块 / 包** | 职责描述（1-3 句） | 设计决策 |
| **类** | 职责描述（1-3 句） | Attributes 说明、使用示例 |
| **公开方法 / 函数** | 功能、参数、返回值 | 异常说明、使用示例 |
| **常量 / 枚举** | 每个值的含义 | — |
| **复杂算法** | 算法思路、时间复杂度 | 参考链接 |

### 1.3 什么不要注释

- 自解释的简单 getter/setter
- 与代码重复的废话注释（如 `# 设置名称` 在 `set_name()` 上）
- 注释掉的代码 — 直接删除，用 Git 历史追溯
- 变更日志 — 用 Git commit message 代替

---

## 2. Python 注释规范

### 2.1 模块注释（必须）

```python
"""
ReAct 循环引擎。

提供基于 Pydantic 模型的 Agent 循环执行，支持 Thought/Action/Observation 三阶段，
所有工具调用均经过 ToolRegistry 白名单校验。

See: docs/specs/agent-core/react-engine.md
"""
```

### 2.2 类注释（必须）

```python
class AgentEngine:
    """ReAct 循环引擎 — 驱动 Agent 完成多轮推理。

    支持两种执行模式：
    - SYNC: 同步执行（适合简单任务）
    - ASYNC: 异步执行（适合长耗时任务）

    Attributes:
        max_iterations: 最大迭代次数
        tools: 注册的工具列表

    Usage::
        engine = AgentEngine(max_iterations=20)
        result = await engine.run(task)
    """
```

### 2.3 函数注释（公开函数必须，Google 风格）

```python
def execute_tool(self, tool_name: str, args: dict[str, Any]) -> ToolResult:
    """执行指定工具并返回结果。

    Args:
        tool_name: 工具注册名称，必须在 ToolRegistry 中已注册。
        args: 工具参数字典，key 为参数名。

    Returns:
        ToolResult，包含执行结果和状态。

    Raises:
        ToolNotFoundError: 当工具名称不在注册表中时抛出。
    """
```

### 2.4 Lint 门禁

使用 **Ruff** `D` 系列规则（pydocstyle）强制检查，详见 [backend/pyproject.toml](../../backend/pyproject.toml) 的 `[tool.ruff]` 配置。

---

## 3. TypeScript / HTML 注释规范

### 3.1 HTML 文件头注释（推荐）

```html
<!--
  chat.html — Agent 对话界面。

  负责展示用户与 Agent 的对话消息，
  通过 fetch 调用后端 /api/ask 接口获取回复。
-->
```

### 3.2 TypeScript/JavaScript 函数注释（导出函数必须，JSDoc 格式）

```typescript
/**
 * 发送消息到 Agent — 调用后端 /api/ask 接口获取回复。
 *
 * @param question - 用户输入的问题
 * @returns Agent 回复的消息对象
 */
export async function sendMessage(question: string): Promise<AgentResponse> {
```

### 3.3 API 层分节注释（推荐）

```typescript
// ─── 类型定义 ───────────────────────────────────────

export interface AgentResponse {
  /** 回复内容 */
  answer: string
  /** 使用的工具列表 */
  tools_used: string[]
}

// ─── API 方法 ───────────────────────────────────────

/**
 * 获取可用工具列表。
 */
export function listTools(): Promise<Tool[]> {
```

---

## 4. 门禁汇总

| 技术栈 | 工具 | 规则 | 级别 |
|--------|------|------|------|
| **Python** | Ruff `D` | `D100` (模块)、`D101` (类)、`D103` (公开函数) | `error` |
| **TypeScript** | eslint-plugin-jsdoc | `jsdoc/require-jsdoc` (导出函数/类) | `warn` |
| **HTML** | 人工 Code Review | 页面级文件头注释 | PR 检查 |

---

## 5. Claude Code 集成

在 Claude Code 中执行 `/commenting-standards` 可快速查阅本规范并检查当前文件是否符合要求。

所有 Claude Code Agent 在生成代码时必须遵循本规范：
- 新增模块/类 → 必须包含文件/类头注释
- 新增公开方法/函数 → 必须包含参数和返回值说明
