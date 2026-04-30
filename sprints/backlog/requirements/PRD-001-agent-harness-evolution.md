---
id: PRD-001
title: Agent Harness 能力演进
version: v1.0
status: draft
priority: P0
release: pool

owners:
  pm: 丁昂
  dev: 丁昂
  qa: self-test

dates:
  created: 2026-04-30

related_specs: []
changelog: ./PRD-001-agent-harness-evolution.changelog.md
---

# Agent Harness 能力演进

## 1. 背景

当前 MClaude ReAct Agent 已具备：
- ReAct 核心循环（模型驱动控制流）
- 工具体系（Pydantic schema + 自动注册 + MCP 懒加载）
- 可观测面板（事件追踪 + JSON 详情）
- 文件上传与自动上下文注入

对照 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 提出的 Agent Harness 架构理念，**核心循环和工具分发已完全对齐**，但以下三个直接影响 Agent 处理复杂任务能力的关键 Harness 层尚未实现。

## 2. 目标

为 Agent 补齐三个核心 Harness 能力，使其能够：
- 持续运行长对话而不崩溃（上下文压缩）
- 在多步任务中保持方向不偏移（任务规划）
- 将复杂问题拆解后并行/串行处理（子 Agent）

## 3. 非目标

- 多 Agent 协作/团队模式（s09-s11）—— 属于高级特性，后续迭代
- Worktree 隔离（s12）—— 当前为单用户场景，不需要
- 后台任务异步执行（s08）—— 当前工具执行耗时可控，优先级较低

---

## 4. 需求详述

### Feature 1：上下文压缩（Context Compaction）

**对应 learn-claude-code**: s06

**问题**：当前 `engine.py` 的 `self.messages` 只增不减。长对话或多工具调用后，消息历史会超出 LLM 上下文窗口限制，导致请求失败或模型表现严重下降。

**方案**：实现三层渐进式压缩机制。

#### AC-1.1 微压缩（Micro-Compact）

- [ ] 每次调用 LLM 前，自动扫描消息历史
- [ ] 将距离当前超过 N 轮（可配置，默认 6 轮）的 `tool` 类型消息的 `content` 替换为摘要占位符，格式：`[已执行: {tool_name}, 结果已省略]`
- [ ] `user`、`assistant`、`system` 类型消息不压缩
- [ ] 压缩过程对 LLM 透明，不产生额外 API 调用
- [ ] 在 `config.yaml` 中添加 `compaction.micro.retention_rounds` 配置项

#### AC-1.2 自动压缩（Auto-Compact）

- [ ] 每次调用 LLM 前估算当前消息历史的 token 数（按字符数粗估：中文 1 字 ≈ 2 token，英文 1 词 ≈ 1.3 token）
- [ ] 当估算 token 数超过阈值（可配置，默认 40000）时触发自动压缩
- [ ] 压缩前将完整消息历史持久化到 `.transcripts/` 目录（JSON 格式），确保可回溯
- [ ] 调用 LLM 生成对话摘要（使用当前配置的模型，system prompt 指示"请将以下对话压缩为关键信息摘要"）
- [ ] 压缩后消息历史替换为：`system` 消息 + 一条 `user` 消息（包含摘要内容）
- [ ] 记录压缩事件到 packet log（`type: "compaction"`），包含压缩前后消息数和估算 token 数
- [ ] 在 `config.yaml` 中添加 `compaction.auto.token_threshold` 配置项

#### AC-1.3 手动压缩工具

- [ ] 新增内置工具 `compact`，LLM 可主动调用以压缩上下文
- [ ] 执行逻辑与自动压缩相同（持久化 → 摘要 → 替换）
- [ ] 返回压缩结果摘要（压缩前/后消息数、估算 token 节省量）

#### AC-1.4 前端可观测

- [ ] 压缩事件在时间线中以独立卡片展示（新 type `compaction`）
- [ ] 卡片显示：压缩前消息数、压缩后消息数、估算 token 节省量

---

### Feature 2：任务规划（TODO / Planning）

**对应 learn-claude-code**: s03 + s07

**问题**：Agent 在执行多步任务时容易漂移——忘记整体目标，陷入某个步骤的细节，或者执行顺序混乱。

**方案**：实现任务管理器 + 漂移提醒机制。

#### AC-2.1 TodoManager

- [ ] 新增 `TodoManager` 类（`domain/agent/todo_manager.py`），管理任务列表
- [ ] 每个任务包含字段：`id`（自增）、`content`（描述）、`status`（`pending` / `in_progress` / `completed`）
- [ ] 约束：同一时间只能有一个任务处于 `in_progress` 状态，设置新任务为 `in_progress` 时自动将之前的 `in_progress` 任务回退为 `pending`
- [ ] 提供操作：`add`（添加任务）、`update`（更新状态）、`list`（列出所有任务）、`clear`（清空）

#### AC-2.2 todo 内置工具

- [ ] 新增内置工具 `todo`，暴露 TodoManager 的能力给 LLM
- [ ] 参数：`action`（add / update / list）、`content`（add 时必填）、`task_id`（update 时必填）、`status`（update 时必填）
- [ ] 返回当前任务列表的格式化文本

#### AC-2.3 漂移提醒（Nag Reminder）

- [ ] 在 ReAct 循环中追踪连续未调用 `todo` 工具的轮数
- [ ] 当连续 N 轮（可配置，默认 4 轮）未调用 `todo` 时，自动注入一条提醒消息到会话历史
- [ ] 提醒消息格式：`[系统提醒] 你已经 {N} 轮没有更新任务状态了。请用 todo 工具检查当前计划，确认是否偏离了目标。`
- [ ] 提醒消息角色为 `user`（确保模型会关注）
- [ ] 提醒注入后轮数计数器重置
- [ ] 在 `config.yaml` 中添加 `planning.nag_interval` 配置项

#### AC-2.4 System Prompt 整合

- [ ] 在 system prompt 中添加任务规划指导："对于多步骤任务，请先用 todo 工具制定计划，每完成一步及时更新状态"
- [ ] 当 TodoManager 中有活跃任务时，将任务列表附加到每轮 LLM 请求的上下文中

#### AC-2.5 前端可观测

- [ ] 提醒事件在时间线中以独立卡片展示（新 type `reminder`）

---

### Feature 3：子 Agent（Subagent）

**对应 learn-claude-code**: s04

**问题**：所有工作在同一个上下文中完成，复杂任务（如"读 5 个文件然后给出方案"）会快速消耗上下文窗口，中间过程的大量信息污染后续推理。

**方案**：实现父子 Agent 模式，子 Agent 在独立上下文中执行任务，只返回精炼结果。

#### AC-3.1 子 Agent 执行器

- [ ] 新增 `SubAgentRunner` 类（`domain/agent/sub_agent.py`），可创建独立的 ReAct 执行环境
- [ ] 子 Agent 拥有独立的消息历史（空数组，不继承父 Agent 上下文）
- [ ] 子 Agent 共享父 Agent 的 `tool_registry`（能使用所有已注册工具）
- [ ] 子 Agent 有独立的最大迭代次数限制（可配置，默认 15）
- [ ] 子 Agent 不能调用 `task` 工具（防止无限递归嵌套）
- [ ] 子 Agent 执行完成后，返回最终回答文本（不返回中间消息历史）

#### AC-3.2 task 内置工具

- [ ] 新增内置工具 `task`，LLM 通过此工具派发子任务
- [ ] 参数：`description`（任务描述，将作为子 Agent 的 user 消息）
- [ ] 执行流程：创建 SubAgentRunner → 运行 → 返回结果摘要
- [ ] 返回格式：`子任务完成。结果：{result}`（截断到 max_chars，可配置，默认 5000）

#### AC-3.3 子 Agent 日志

- [ ] 子 Agent 的所有 packet 日志共享父 Agent 的 packet_logger
- [ ] 子 Agent 的日志事件增加 `sub_agent: true` 标识字段
- [ ] 子 Agent 的迭代编号独立计数（不与父 Agent 冲突）

#### AC-3.4 前端可观测

- [ ] 子 Agent 的事件在时间线中通过视觉标识区分（如左边框颜色不同、或添加 `SUB` 标签）
- [ ] 支持按子 Agent 筛选/折叠事件

---

## 5. 配置项汇总

以下配置项添加到 `config.yaml`：

```yaml
compaction:
  micro:
    retention_rounds: 6       # 保留最近 N 轮的工具结果，更早的自动摘要
  auto:
    token_threshold: 40000    # 估算 token 超过此值触发自动压缩

planning:
  nag_interval: 4             # 连续 N 轮未更新任务状态时注入提醒

sub_agent:
  max_iterations: 15          # 子 Agent 最大迭代次数
  max_result_chars: 5000      # 子 Agent 返回结果最大字符数
```

## 6. 技术约束

- **架构边界**：新增代码遵守现有分层规则，domain 层不依赖 infrastructure
  - `TodoManager`、`SubAgentRunner` 放在 `domain/agent/`
  - `compact` / `todo` / `task` 工具放在 `infrastructure/tools/builtin/`
  - 配置项通过 `infrastructure/config/settings.py` 加载
- **向后兼容**：所有新功能默认启用但不强制使用——LLM 不调用相关工具时，行为与现有版本完全一致
- **测试**：每个 Feature 至少覆盖正常流程和边界场景（如压缩空历史、单任务 TODO、子 Agent 迭代超限）

## 7. 实施优先级

| 阶段 | Feature | 理由 |
|------|---------|------|
| P0 | 上下文压缩 | 阻断性问题：没有压缩，长对话必崩 |
| P1 | 任务规划 | 显著提升多步任务成功率 |
| P2 | 子 Agent | 前置依赖上下文压缩，组合后威力最大 |

## 8. 验收标准总览

| Feature | AC 数量 | 关键验收点 |
|---------|---------|-----------|
| 上下文压缩 | 4 | 微压缩不丢关键信息、自动压缩有持久化备份、前端可见压缩事件 |
| 任务规划 | 5 | 单 in_progress 约束生效、漂移提醒按配置触发、prompt 引导有效 |
| 子 Agent | 4 | 独立上下文隔离、无递归嵌套、日志可区分 |
