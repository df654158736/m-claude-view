---
name: prd-status
description: "PRD 发布版本追踪与需求点（AC）进度聚合。按发布版本（v2026-04-30 等）和需求池（pool）组织 PRD，生成 PRD-STATUS.md 矩阵视图。AUTO-TRIGGER：用户问'需求进度如何'/'这个版本做到哪了'/'PRD-XXX 状态'，或 /doc-sync / /doc-sync-after-dev 末尾自动调用。手动命令：/prd-status、/prd-status update、/prd-status v2026-04-30、/prd-status prd PRD-001、/prd-status ac AC-001-01、/prd-status assign、/prd-status accept、/prd-status check、/prd-status migrate。"
---

# PRD 状态追踪（/prd-status）

## 核心模型

三级追踪颗粒度：

```
Release (v2026-04-30, v2026-05-30, pool)
  └─ PRD (PRD-001 工具策略引擎)
       └─ AC (AC-001-01 需求点/验收单位)
            └─ Task (tasks-丁昂.md 里 [x]/[ ] 的 checkbox)
```

**状态聚合方向**：Task → AC → PRD → Release（由 skill 自动算，人不手填进度）

**状态机**：

```
AC:  ⬜ 未开始 → 🟡 开发中 → 🟢 已自测 → ✅ 已验收 (PM 确认)
                                    ↓
                            🔴 验收未通过

PRD:  draft → reviewed → in-dev → delivered
                              ↓
                         deferred / archived
```

---

## 目录结构

```
sprints/backlog/requirements/
├── application/                                  ← PRD 原文所在（位置不动）
│   ├── Agent-Core/PRD-001-*.md
│   └── Tool-System/PRD-002-*.md
└── _releases/                                    ← 版本视图层（本 skill 管理）
    ├── v2026-04-30/
    │   ├── PRD-STATUS.md                         ← 自动生成
    │   ├── release-plan.md                       ← 人手写（版本目标）
    │   └── change-log.md                         ← 人手写（范围变更）
    ├── v2026-05-30/
    │   ├── PRD-STATUS.md
    │   └── release-plan.md
    └── pool/
        └── PRD-STATUS.md                         ← 需求池视图
```

> `_releases/` 用下划线前缀让它排在目录顶部。

---

## 命令集

| 命令 | 作用 | 是否落盘 |
|------|------|---------|
| `/prd-status` | 全版本一屏概览（所有 release + pool 的总体进度 + 风险项） | 不落盘，打印到屏幕 |
| `/prd-status v2026-04-30` | 查看特定版本详情 | 不落盘 |
| `/prd-status prd PRD-001` | 查看 PRD 级进度（展开所有 AC） | 不落盘 |
| `/prd-status ac AC-001-02` | 查单个需求点详情（关联 task 清单） | 不落盘 |
| `/prd-status update` | **全量重算**，重写所有 PRD-STATUS.md 和 PRD 内的 AC 状态表 | ✅ 落盘 |
| `/prd-status update v2026-04-30` | 只重写单个版本 | ✅ 落盘 |
| `/prd-status assign PRD-030 v2026-05-30` | 把 PRD 分配到版本（改 frontmatter） | ✅ 落盘 |
| `/prd-status mark-tested AC-001-01 "证据"` | Dev 标 AC 自测通过（校验 DoD 六条） | ✅ 落盘 |
| `/prd-status accept AC-001-01` | PM 标 AC 验收通过（前置检查自测通过） | ✅ 落盘 |
| `/prd-status reject AC-001-01 "理由"` | PM 标 AC 验收不通过 | ✅ 落盘 |
| `/prd-status check` | 一致性校验（六类异常） | 不落盘，报告 |
| `/prd-status release new v2026-05-30` | 启动新版本目录 | ✅ 落盘 |
| `/prd-status release close v2026-04-30` | 归档已发布版本 | ✅ 落盘 |
| `/prd-status migrate` | 历史 PRD 批量加 frontmatter + AC 重编号（先出草表） | ✅ 落盘（需审批） |
| `/prd-status pm-inbox` | 列出"Dev 标完成但 PM 还没验收"的 AC | 不落盘 |
| `/prd-status dev-inbox` | 列出"分给我开发的 AC 清单" | 不落盘 |

---

## 核心工作流

### `/prd-status update` — 核心聚合逻辑

```
1. 扫描所有 PRD
   glob: sprints/backlog/requirements/**/PRD-*.md
   解析 YAML frontmatter → {prd_id, release_version, status, priority, owners, dates, ...}
   解析"## 需求点"章节 → AC 列表 [{ac_id, description, priority, ...}]

2. 扫描所有任务文件
   glob: sprints/active/**/tasks-*.md
   解析每个 task 的 "关联需求点" 和 checkbox [x]/[ ]
   建立 AC → Task 反向索引

3. 为每个 AC 聚合状态
   - 关联 0 个 task        → ⬜ 未分配
   - 所有 checkbox [x]     → 🟢 已自测（等 PM 验收）
   - 部分 [x]              → 🟡 开发中
   - 全部 [ ]              → ⬜ 已排期未开工
   - PRD 内已标 "已验收"    → ✅
   - PRD 内已标 "验收未通过" → 🔴

4. 为每个 PRD 聚合状态
   - 所有 P0/P1 AC ✅ → delivered
   - 有 AC 🟡/🟢     → in-dev
   - 全 ⬜           → planned
   - P0 AC 未完成 & 距发布 <7 天 → at-risk

5. 按 release_version 分组渲染
   写入 _releases/v{日期}/PRD-STATUS.md
   pool 归属的 PRD 写入 _releases/pool/PRD-STATUS.md

6. 回写每个 PRD 内的"需求点"章节的自动字段
   - AC 状态、关联任务、开发开始/完成时间
   - PRD frontmatter 的 last_updated / actual_start / actual_complete
```

### `/prd-status mark-tested` — 标记 AC 自测通过

```
用法: /prd-status mark-tested AC-001-01 "证据链接或说明"

流程:
1. 读 PRD 的 AC 章节，确认 AC 存在且当前状态为 🟡 开发中
2. 校验 Definition of Done 六条（详见 docs/standards/AC-tracking.md §10.1）：
   - 单元测试通过
   - 契约/集成测试通过
   - /qg 绿灯
   - 主流程手动验证
   - 代码已合并主干
   - 无 console error/warning
3. 全达 → 写入 PRD AC 元数据块：
   > **自测通过**: {YYYY-MM-DD} {git-id} · {qg-report-id} · commit@{short-sha}
4. 未达 → 报告哪项不满足，保持状态为 🟡
5. 刷新 PRD-STATUS.md 该 AC 的"自测状态"列

来源:
- 方式 A: /qg 绿灯后自动调用
- 方式 B: Dev 对话中手动声明触发
```

### `/prd-status accept` — PM 验收通过

```
用法: /prd-status accept AC-001-01 [可选:验收说明]

前置检查 (硬约束):
- AC 的"自测通过"字段必须已填写
- 未填 → 阻断，提示 "Dev 未标自测通过，不能跳过验收环节"

流程:
1. 读 PRD 的 AC 章节，确认已自测
2. 写入 PRD AC 元数据块:
   > **验收通过**: {YYYY-MM-DD} {PM-git-id}
3. AC 状态: 🟢 已自测 → ✅ 已验收
4. 刷新 PRD-STATUS.md
5. 如果该 AC 所在 PRD 所有 AC 都 ✅，PRD 状态自动 in-dev → delivered
```

### `/prd-status reject` — PM 验收未通过

```
用法: /prd-status reject AC-001-01 "退回理由"

流程:
1. 写入 PRD AC 元数据块:
   > **验收退回**: {YYYY-MM-DD} {PM-git-id} · 理由: {reason}
2. 清除"自测通过"字段（强制重新自测）
3. AC 状态: 🟢 → 🔴 验收未通过
4. 追加到 .changelog.md
5. 建议 dev 修复后重新跑 /qg 再标 mark-tested
```

### 主动提醒规则（skill 内置）

Claude 在对话中自动检测以下场景并主动开口：

```
场景 1: AC 所有关联 task checkbox 都 [x] 但"自测通过"字段未填
  → 问 dev: "AC-XXX 看起来实现完了，跑过 /qg 吗？要不要标自测通过？"

场景 2: AC "自测通过"已填但"验收通过"未填 超过 2 天
  → 提醒 PM: "AC-XXX 已自测 2 天了（dev=xxx），要不要验收？"

场景 3: 距发布日 ≤ 7 天，且仍有 P0 AC 状态为 🟡 或 🔴
  → 预警: "距 v2026-04-30 还有 N 天，M 个 P0 AC 未完成: [清单]"

场景 4: Dev 在对话中说 "做完了" / "测过了"
  → 主动: "确认一下是哪个 AC 完成？我帮你走 /prd-status mark-tested"
```

### `/prd-status check` — 六类异常

| 异常 | 检测方式 | 严重性 |
|------|---------|-------|
| 孤儿 Task | task 文件未写 `关联需求点`，或引用不存在的 AC ID | 🔴 阻断 |
| 失踪 AC | task 引用了 `AC-001-99`，但 PRD-001 中没这个 AC | 🔴 阻断 |
| 未覆盖 AC | PRD 状态 `in-dev`，但某 P0 AC 无任何 task 引用 | 🟡 预警 |
| 状态漂移 | AC 标 ✅ 但关联 task 还有 ⬜ | 🔴 阻断 |
| 跨版本穿越 | task 在 v2026-04-30 Wave 里，但引用的 AC 属于其他版本的 PRD | 🟡 预警 |
| Changelog 缺失 | AC 描述变了（git diff）但 `.changelog.md` 未更新 | 🟡 预警 |

### `/prd-status migrate` — 历史 PRD 迁移

**不直接改写**，先出草表让用户审阅：

```
Step 1: 扫描所有历史 PRD，解析现有 frontmatter（blockquote 格式）
Step 2: 解析 "## 验收标准" 段，抽取现有 AC-XX
Step 3: 按启发式给每个 PRD 建议 release_version：
        - 在 sprints/active/ 中有 task 引用 且 最近有活跃提交  → v2026-04-30
        - 所有关联任务 ✅ 且 PROGRESS.md 已标 delivered         → v2026-04-30 (delivered)
        - 有详设但无 task                                       → v2026-05-30
        - 仅草稿、无详设                                         → pool
        - 标记 archived / 废弃                                  → archived

Step 4: 生成 _releases/migration-draft.md 草表：
        | PRD | 现状态 | 建议 release | 建议 status | AC 重编号预览 | 推荐负责人 |

Step 5: 等用户在草表中批改 → /prd-status migrate apply
Step 6: 批量写入每个 PRD 的 YAML frontmatter + AC 章节重编号
Step 7: 生成首版 PRD-STATUS.md
```

---

## PRD-STATUS.md 输出格式

### 版本级（如 `_releases/v2026-04-30/PRD-STATUS.md`）

```markdown
# PRD-STATUS — v2026-04-30

> **发布目标日期**: 2026-04-30
> **版本状态**: in-dev
> **版本负责人 (RM)**: 丁昂
> **生成时间**: 2026-04-16 14:32
> **剩余工作日**: 10 天
> **总体进度**: 58% (2/3 PRD delivered, 15/20 AC 完成)
> **风险等级**: 🟡 黄

## PRD 进度总览

| PRD | 标题 | 优先级 | 状态 | AC 进度 | Task 进度 | 实际开始 | 预计完成 | 需求负责人 | 开发负责人 | 风险 |
|-----|------|--------|------|--------|----------|---------|---------|----------|----------|------|
| PRD-001 | 工具策略引擎 | P0 | ✅ delivered | 8/8 | 12/12 | 2026-03-20 | 2026-03-28 | 丁昂 | 丁昂 | - |
| PRD-002 | 多轮对话管理 | P0 | 🟡 in-dev | 5/8 | 10/15 | 2026-04-01 | 2026-04-25 | 丁昂 | 丁昂 | - |
| PRD-003 | ReAct 推理链路 | P1 | 🟡 in-dev | 3/6 | 6/10 | 2026-04-05 | 2026-04-28 | 丁昂 | 丁昂 | 时间紧 |

## 按状态聚合

- ✅ delivered: 1
- 🟡 in-dev: 2
- ⬜ planned: 0
- 🔴 at-risk: 0

## 风险 AC 清单（P0 & 未完成 & 距发布 <14 天）

| 需求点ID | PRD | 描述 | 状态 | 开发负责人 | 阻塞原因 |
|---------|-----|------|------|----------|---------|
| AC-002-03 | PRD-002 | 上下文窗口溢出处理 | ⬜ | 未分配 | 待 丁昂 排期 |
| AC-003-05 | PRD-003 | 思维链可视化 | 🟡 | 丁昂 | 详设未定稿 |

## 最近变更（由 doc-sync 追加）

- 2026-04-16 丁昂: PRD-002 §3.2 新增 AC-06
- 2026-04-10 丁昂: PRD-010 从本版本移至 v2026-05-30
```

### AC 级明细表（每个 PRD 一张，跟在总览后面）

每份 PRD 的 AC 明细表列定义（11 列），**每行 1:1 对应 decisions-ac-level.md 中标 `[x] <version>` 的项**：

```markdown
### PRD-{编号} {标题} — {进度} {N/M} ({X%})

| AC ID | 标题 | P | 开发状态 | 验收状态 | dev | 详设 | 关联任务 | 关联代码 | 预估 | 实际 |
|-------|------|---|---------|---------|-----|------|---------|---------|------|------|
| AC-001-01 | 工具注册与发现机制 | P0 | ✅ 完成 | ✅ 已验收 | 丁昂 | SPEC-BE-014 §3.1 | tasks-丁昂.md#T1 | backend/src/infrastructure/tools/base.py | 2d | 2.5d |
| AC-001-02 | 工具执行策略路由 | P0 | 🟢 已自测 | 未验收 | 丁昂 | SPEC-BE-014 §3.2 | tasks-丁昂.md#T2 | backend/src/domain/agent/engine.py | 1.5d | 1.5d |
| AC-001-03 | 工具失败重试与降级 | P0 | 🟡 进行中 | 未验收 | TBD | SPEC-FE-005B §4 | 未分配 | 未实现 | 3d | — |
```

### AC 状态图示速查

| 图示 | 开发状态 | 触发条件 |
|------|---------|---------|
| ⬜ | 未开始 | 无关联 task，或所有 checkbox `[ ]` |
| 🟡 | 进行中 | 部分 checkbox `[x]`，自测未过 |
| 🟢 | 已自测 | 所有 task 完成 + DoD 六条全达（见 AC-tracking.md §10.1） |
| ✅ | 已验收 | PM 运行 `/prd-status accept` 后 |
| 🔴 | 验收未通过 | PM 运行 `/prd-status reject` 后 |

### 字段来源（AC 明细表每列）

| 列 | 数据来源 | 填写方 |
|----|---------|-------|
| AC ID / 标题 / 优先级 | PRD 的 AC 章节标题 | PM 手填 |
| 开发状态 | skill 扫 task checkbox + `.changelog.md` | 自动 |
| 验收状态 | PRD AC 元数据块的 `验收通过` 字段 | PM 触发 `accept` |
| dev | AC 元数据块 `负责 dev=xxx` | PM 手填 |
| **详设** | AC 元数据块 `详设 SPEC-BE-XXX §N` | PM 手填；变更走 `/doc-sync` |
| **关联任务** | skill 扫 `sprints/active/**/tasks-*.md` 里 `(AC-XXX-YY)` 引用 | 自动聚合 |
| **关联代码** | 从 task 文件反查 commit 的代码变更路径；或 `/qg` 跑测时记录的主路径 | 自动 |
| 预估 | AC 元数据块 `预估 Nd` | PM 手填 |
| 实际 | 聚合关联 task 的 git log 时长（或 dev 在 task 文件标注） | 自动 |

### 详设 & 代码的追踪粒度

**明确支持到 AC 级**（不是 PRD 级）：

| 追踪对象 | 颗粒度 | 谁填 | 存储位置 |
|---------|--------|------|---------|
| **详设 SPEC** | AC 对应到 SPEC 文件的具体 **§章节** | PM 写 PRD 时手填 | PRD 正文 AC 元数据块 |
| **关联代码** | AC 对应的**主实现文件路径**（可多个，逗号分隔）| skill 自动聚合 | PRD 正文 AC 元数据块 + STATUS 表列 |
| **关联任务** | AC 对应到 task 文件的**具体 checkbox 行** | Dev 在 task 勾 checkbox 时引用 `(AC-XXX-YY)` | skill 扫描 |

**追踪示例**（取一条真实 AC）：

```markdown
### AC-001-01 工具注册与发现机制  `P0`

> **状态**: 开发✅ · 验收已验收
> **负责**: dev=丁昂 · qa=self-test
> **详设**: SPEC-BE-014 §3.1 工具注册算法, SPEC-FE-005B §4.2 工具列表组件  ← 支持多 SPEC 多章节
> **关联任务**: tasks-丁昂-2026-04-10.md#T1, tasks-丁昂-2026-04-11.md#T3
> **关联代码**: backend/src/infrastructure/tools/registry.py, backend/src/domain/agent/tool_resolver.py
> **预估**: 2 人日 · 实际: 2.5 人日
> **验收通过**: 2026-04-15 丁昂
```

### 需求池（`_releases/pool/PRD-STATUS.md`）

```markdown
# 需求池 — Requirement Pool

收录未进入发布版本的 PRD。

| PRD | 标题 | 优先级 | 状态 | 预估工作量 | 建议版本 | 评估结论 | 需求负责人 |
|-----|------|--------|------|-----------|---------|---------|----------|
| PRD-030 | XX | P1 | draft | 10d | v2026-05-30 | 待评估 | 丁昂 |
| PRD-040 | YY | P2 | backlog | 5d | 未定 | 已澄清，等排期 | 丁昂 |
```

---

## 与其他 Skill 的集成

| Skill | 集成方式 |
|------|---------|
| `/PRD` | 写 PRD 时强制拆 AC；新增 `add-ac` 子命令给已有 PRD 补 AC（见 AC-enhancement-for-PRD-skill.md） |
| `/doc-sync` | 末尾**自动**调用 `/prd-status update`（增量） |
| `/doc-sync-after-dev` | 末尾**自动**调用 `/prd-status update` + `/prd-status check`（全量 + 校验） |
| `/sprint-management` | 创建 task 时，模板强制写 `关联需求点: AC-XXX`；task 状态变更时调 `/prd-status update` |

---

## 输入输出规范

### PRD frontmatter（作者手填）

遵循 [docs/standards/PRD-frontmatter.md](../../../docs/standards/PRD-frontmatter.md)

### AC 拆分与格式

遵循 [docs/standards/AC-tracking.md](../../../docs/standards/AC-tracking.md)

### Task 引用 AC

遵循 [docs/standards/AC-tracking.md §3 Task 引用规范](../../../docs/standards/AC-tracking.md#3-task-引用-ac-的规范)

---

## 语言规则

**中文优先** — 与用户交互、PRD-STATUS.md 渲染、错误提示都用中文。专业术语保持英文（PRD/AC/release/pool/frontmatter 等）。

---

## 最小可用版本（MVP）

首版只实现这些命令，其他命令等需要时再加：

1. `/prd-status migrate` — 历史 PRD 迁移（一次性）
2. `/prd-status update` — 聚合重算
3. `/prd-status` — 全版本概览
4. `/prd-status v{日期}` — 特定版本
5. `/prd-status check` — 一致性校验

暂缓：`accept/reject/pm-inbox/dev-inbox/release new/close`（等流程跑起来、有 QA 时再加）

---

## 定时扫描（兜底机制）

建议配合 `/schedule` 或外部 cron：

```
每日 09:00 — /prd-status check  （发现问题主动提醒）
每周一 09:00 — /prd-status    （打印全局概览给 RM 看）
```

MVP 期间**不配定时**，先手动跑。运行一两周后再上。
