# PRD Frontmatter 规范

> **适用范围**：`sprints/backlog/requirements/**/PRD-*.md`
> **格式**：YAML frontmatter（标准 Markdown frontmatter，三横线包裹）
> **机读**：本规范的字段被 `/prd-status` skill 解析，也被 IDE 插件（如 Obsidian）直接显示
> **维护方**：PM 手填必填字段，`/prd-status update` 自动回写计算字段

---

## 1. 最小必填示例

```yaml
---
id: PRD-002D
title: 多层级建模与关联穿透下钻
version: v1.0
status: in-dev
priority: P0
release: 2026-04-30

owners:
  pm: 丁昂
  dev: 丁昂
  qa: self-test          # 暂无独立 QA，研发自测 + PM 验收

stakeholders:
  - 产品运营团队

dates:
  created: 2026-03-15
  reviewed: 2026-03-25
  planned_start: 2026-04-01
  planned_complete: 2026-04-25

estimate_days: 10

related_specs:
  - docs/specs/agent-core/SPEC-001-react-engine.md
  - docs/specs/tool-system/SPEC-002-tool-registry.md

changelog: ./PRD-002D-Multi-Hierarchy-Modeling-and-Drilldown.changelog.md
---
```

---

## 2. 字段清单

### 2.1 身份字段（必填，不可变）

| 字段 | 类型 | 示例 | 说明 |
|------|------|------|------|
| `id` | string | `PRD-002D` | 全局唯一 PRD 编号，一旦确定不改 |
| `title` | string | `多层级建模与关联穿透下钻` | 简洁标题，与文件名呼应 |

### 2.2 版本与状态（必填，动态）

| 字段 | 类型 | 取值 | 说明 |
|------|------|------|------|
| `version` | string | `v1.0`, `v1.1`, `v2.0` | 遵循 `/doc-sync-after-dev` 规则 6 的版本号规则 |
| `status` | enum | 见下表 | PRD 当前生命周期状态 |
| `priority` | enum | `P0` / `P1` / `P2` | 业务优先级 |
| `release` | string | `2026-04-30` / `pool` / `archived` | 所属发布版本；未排期用 `pool` |

**`status` 取值**：

| 值 | 含义 | 触发条件 |
|----|------|---------|
| `draft` | 初稿 | PRD 刚创建，未评审 |
| `reviewed` | 已评审 | PM 与干系人对齐完毕，AC 完整、冻结 |
| `in-dev` | 开发中 | 至少一个 task 在开发 |
| `delivered` | 已交付 | 所有 P0/P1 AC ✅（PM 已验收） |
| `deferred` | 延期 | 从当前版本移出至未来版本 |
| `archived` | 归档 | 不做了 / 被替代 |

> 从 `reviewed` 进入 `in-dev` 后，**AC 清单冻结**。再改 AC = 需求变更，走 `/doc-sync` 流程。

### 2.3 负责人字段（必填）

```yaml
owners:
  pm: 丁昂                 # 需求负责人，git id
  dev: 丁昂                # 开发负责人，git id
  qa: self-test            # 测试负责人，暂时用 self-test 标识研发自测
```

**特殊值**：
- `qa: self-test` — 当前无独立 QA，研发自测 + PM 验收
- `dev: TBD` — 尚未分配开发
- `pm: TBD` — 尚未分配 PM（不推荐，一般都知道是谁）

### 2.4 干系人（可选）

```yaml
stakeholders:
  - 产品运营团队
  - 数据中台团队
  - 客户 A
```

用于记录需求来源与利益方，PRD-STATUS 输出时会列出。

### 2.5 时间字段

**必填（PM 手填）**：

```yaml
dates:
  created: 2026-03-15            # PRD 首稿日期
  reviewed: 2026-03-25           # 评审通过日期（可选，status 进入 reviewed 时填）
  planned_start: 2026-04-01      # 计划开始
  planned_complete: 2026-04-25   # 承诺交付日
```

**自动回写（`/prd-status update` 写入）**：

```yaml
dates:
  # ...（以上人工字段）
  actual_start: 2026-04-02       # 关联的第一个 task 首次提交日
  actual_complete: null          # 所有 AC ✅ 时写入
  last_updated: 2026-04-16       # 最近一次 frontmatter 变更
  last_active: 2026-04-16        # 关联 task 的最近活跃日
```

### 2.6 工作量（可选）

```yaml
estimate_days: 10                # 人日估算（PM 填）
actual_days: 12                  # 自动回写，基于 task 累计
```

### 2.7 关联文档（必填）

```yaml
related_specs:                   # 关联详设文档路径（相对仓库根）
  - docs/specs/agent-core/SPEC-*.md
  - docs/specs/tool-system/SPEC-*.md

changelog: ./PRD-002D-xxx.changelog.md   # 与 doc-sync 规则 1 一致
```

### 2.8 衍生指标（自动回写，PM 不填）

以下字段由 `/prd-status update` 计算后回写，**PM 不要手动编辑**：

```yaml
derived:
  ac_total: 12                   # AC 总数
  ac_done: 8                     # 已完成（✅）
  ac_in_progress: 2              # 🟡 + 🟢
  ac_blocked: 0                  # 🔴
  task_total: 22
  task_done: 15
  risk_level: yellow             # green / yellow / red
  aggregated_status: in-dev      # 由 AC 聚合得出，会覆盖手填的 status
```

---

## 3. 完整范例（含自动字段）

```yaml
---
id: PRD-002D
title: 多层级建模与关联穿透下钻
version: v1.2
status: in-dev
priority: P0
release: 2026-04-30

owners:
  pm: 丁昂
  dev: 丁昂
  qa: self-test

stakeholders:
  - 产品运营团队

dates:
  created: 2026-03-15
  reviewed: 2026-03-25
  planned_start: 2026-04-01
  planned_complete: 2026-04-25
  actual_start: 2026-04-02
  actual_complete: null
  last_updated: 2026-04-16
  last_active: 2026-04-16

estimate_days: 10
actual_days: 6.5

related_specs:
  - docs/specs/agent-core/SPEC-001-react-engine.md
  - docs/specs/tool-system/SPEC-002-tool-registry.md

changelog: ./PRD-002D-Multi-Hierarchy-Modeling-and-Drilldown.changelog.md

derived:
  ac_total: 12
  ac_done: 8
  ac_in_progress: 2
  ac_blocked: 0
  task_total: 22
  task_done: 15
  risk_level: green
  aggregated_status: in-dev
---

# 多层级建模与关联穿透下钻

（正文）
```

---

## 4. 迁移规则（从老 blockquote 格式）

老格式：

```markdown
> **文档编号**: PRD-002D
> **版本**: v1.0
> **状态**: in-dev
> **Changelog**: [变更日志](./PRD-002D-xxx.changelog.md)
```

`/prd-status migrate` 自动转换为新 YAML frontmatter，转换规则：

| 老字段 | 新字段 |
|-------|-------|
| 文档编号 | `id` |
| 文档标题（从 `# 标题` 取） | `title` |
| 版本 | `version` |
| 状态 | `status`（规范化 `进行中` → `in-dev`） |
| 优先级 | `priority` |
| 创建日期 | `dates.created` |
| 更新日期 | `dates.last_updated` |
| 作者 | `owners.pm` |
| Changelog | `changelog` |
| 相关 Plane | 弃用（关联 SPEC 已足够） |

> 迁移时**保留**老 blockquote 元数据区在正文顶部作为人类可读备份，直到下一次 `/doc-sync` 再彻底清除。

---

## 5. 字段校验（`/prd-status check` 执行）

| 规则 | 严重性 |
|------|-------|
| `id` 缺失或格式错（非 `PRD-\w+`） | 🔴 阻断 |
| `release` 既不在 `_releases/` 中也不是 `pool`/`archived` | 🔴 阻断 |
| `status: in-dev` 但 `owners.dev: TBD` | 🟡 预警 |
| `status: delivered` 但 `dates.actual_complete: null` | 🔴 阻断 |
| `priority: P0` 但 `dates.planned_complete` 早于今天 & `status` 非 delivered | 🔴 阻断（超期） |
| `related_specs` 列表为空且 `status >= reviewed` | 🟡 预警 |

---

## 6. 与 Obsidian/IDE 插件的兼容

YAML frontmatter 是行业标准，以下工具开箱即用：
- **Obsidian** — Properties 面板可视化编辑
- **VS Code + Markdown All in One** — 折叠/渲染
- **Jekyll / Hugo** — 如果将来做文档站点，无需转换
- **dataview/templater** — 若使用 Obsidian，可写查询（如"列出所有 release=2026-04-30 的 PRD"）
