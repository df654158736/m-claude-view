---
name: need-to-code
description: |
  需求 ↔ 文档 ↔ 代码 全链路定位与改动地图生成器。给一句需求 / PRD / AC / SPEC / 代码文件，
  反向/正向跳转到所有关联文档与代码符号，输出"改动地图"（主要修改文件 + 影响面 + 同步文档清单 +
  推荐 next skill），让 Agent 在 30 秒内把"提需求"变成"知道动哪里"。
  AUTO-TRIGGER：用户说"我想改 XX"/"做 XX 功能要动哪里"/"PRD-XXX 怎么落"/"AC-XXX 在哪实现"/
  "这个文件属于哪个需求"/"XXX 影响面"/"这块代码怎么来的"，或 Agent 拿到一份新需求/Bug 准备开工
  但还没定位代码时。
  手动命令：/need-to-code "<需求描述>"、/need-to-code prd PRD-001、/need-to-code ac AC-001-01、
  /need-to-code spec SPEC-BE-014、/need-to-code from-code <文件:行号>、/need-to-code map。
user-invocable: true
---

# /need-to-code — 需求到代码的全链路定位

## 一句话定位

**输入**：自然语言需求 / PRD-XXX / AC-XXX / SPEC-XXX / 代码文件路径
**输出**：改动地图（要动哪些文件 + 影响面 + 要同步哪些文档 + 推荐下一步 skill）

> 不写代码、不改文档，只做"提需求 → 找到一切相关物 → 给出动手蓝图"。
> 配合 `/prd-status`（拉需求状态）+ `/spec-prelaunch-review`（开工前核验）+ `/doc-sync`（改完同步）使用。

---

## 何时用

### 触发场景

| 场景 | 用法 |
|------|------|
| 用户拿到一句模糊需求 | `/need-to-code "支持工具执行超时控制"` |
| 用户给出 PRD 编号准备开工 | `/need-to-code prd PRD-001` |
| 用户给出 AC 编号要做最小开发单元 | `/need-to-code ac AC-001-01` |
| 用户拿到 SPEC 但不知道改哪些代码 | `/need-to-code spec SPEC-BE-014` |
| 用户在代码里看到陌生类，想知道它属于哪个需求 | `/need-to-code from-code backend/src/infrastructure/tools/registry.py:45` |
| 团队 RM 想看全项目"需求—代码"映射图 | `/need-to-code map` |

### 不触发的场景

- 用户已经明确知道改哪个文件、只是要写代码 → 直接写
- 单纯查 PRD 进度 → 用 `/prd-status`
- 单纯做代码影响面分析（无需求侧） → 用 `gitnexus-impact-analysis`
- spec 已对齐、要核验"按 spec 写代码会不会编译失败" → 用 `/spec-prelaunch-review`

---

## 命令集

| 命令 | 入口类型 | 是否落盘 | 典型耗时 |
|------|---------|---------|---------|
| `/need-to-code "<自然语言>"` | 文本 → 语义检索 PRD/AC | 否 | 30~60s |
| `/need-to-code prd PRD-001` | PRD 编号 | 否 | 20s |
| `/need-to-code ac AC-001-01` | AC 编号（**最精确**） | 否 | 15s |
| `/need-to-code spec SPEC-BE-014` | SPEC 编号 | 否 | 30s |
| `/need-to-code from-code <文件:行号>` | 反向：代码 → 需求 | 否 | 30s |
| `/need-to-code map` | 全量构建关系图 | ✅ `docs/_index/relation-map.json` | 2~5min |
| `/need-to-code map refresh` | 增量刷新 | ✅ 同上 | 30s |
| `/need-to-code orphans` | 列出"无需求关联的代码"或"无代码关联的 AC" | 否 | 1min |

---

## 标准工作流（按入口类型）

### 老 PRD 格式的退化策略（重要）

> **现状**：仓库内 PRD 可能仍为老 blockquote 元数据格式，未迁移到 YAML frontmatter。`/prd-status migrate` 命令尚未跑过。
> **影响**：工作流 B/C 中"读 frontmatter.related_specs"和"读 AC 元数据块"会失败。
> **退化策略**：本 skill 必须能在老格式下输出**降级版**改动地图，不得直接报错让用户去跑 migrate。

**退化解析规则**（按优先级回落）：

| 期望字段 | 新格式（YAML） | 老格式回落 |
|---------|---------------|-----------|
| 关联 SPEC | `frontmatter.related_specs` | blockquote `> **关联文档**:` / `> **相关详设**:` 中的 markdown link 或 `SPEC-XXX` 编号 |
| 关联 PRD（反向） | `frontmatter.related_prds` | blockquote `> **依赖需求**:` / `> **基础文档**:` 中的 `PRD-XXX` |
| AC 列表 | `## 需求点` 章节 + `### AC-XXX-YY` | `## 验收标准` / `## 功能需求` 章节 + 列表项（**粗粒度，无 ID**）|
| AC 状态 | AC 元数据 `> **状态**:` | 不可解析 → 标"未知"|
| AC ↔ SPEC 引用 | AC 元数据 `> **详设**: SPEC-XX §Y` | 整 PRD 共享 `关联文档` 链接 → SPEC 章节定位粒度退到"全 SPEC" |

**降级版改动地图的 banner**（必须在输出顶部加）：

```markdown
> ⚠ 本 PRD 仍为老格式，AC 粒度退化为"全 PRD 章节级"。
> 影响：影响面分析准确度下降；推荐尽快跑 `/prd-status migrate PRD-XXX` 升级。
```

**退化模式下的额外步骤**：

1. 工作流 B Step 1 解析失败 → fall back 到 blockquote 解析
2. 工作流 C 入口失效（无 AC ID） → 用户必须给 PRD 编号 + 章节号（如 `PRD-001 §6.4`）
3. 工作流 D 不受影响（SPEC 顶部 blockquote 早就用 `> **关联需求**:` 反向引用）— **这是当前最稳的入口**
4. 工作流 E 不受影响（反查走 commit / SPEC，不依赖 PRD frontmatter）
5. 工作流 F (`map`) 跑出来的图谱必须标记每个 PRD 的 `format_version: legacy | yaml`，让 RM 看到迁移进度

**何时建议用户先跑 migrate**：

- 用户连续两次走工作流 B/C 都被退化 → 在响应末尾追加："已退化解析 N 次，建议批量跑 `/prd-status migrate` 一次性升级所有 PRD"
- `/need-to-code map` 跑完发现 legacy 比例 > 50% → 在统计输出里高亮提示

---

### 工作流 A：自然语言入口

```
用户: /need-to-code "支持工具执行超时控制"
  ↓
Step 1：语义检索 PRD/AC
  - Glob sprints/backlog/requirements/**/PRD-*.md
  - Grep 关键词组合：工具 + 超时 + 执行 / timeout / tool
  - 命中 top-3 候选 AC，问用户："是不是 AC-001-01 / AC-002-03 这两个？"
  ↓
Step 2：用户确认锚点 → 跳到工作流 C（AC 入口）
```

### 工作流 B：PRD 入口

```
用户: /need-to-code prd PRD-001
  ↓
Step 1：读 PRD 全文
  - 解析 frontmatter → release / status / owners / related_specs
  - 解析 "## 需求点" 章节 → 全部 AC 列表
  ↓
Step 2：聚合 AC 状态
  - 调 /prd-status prd PRD-001（直接复用，不重复实现）
  - 拿到每个 AC 的开发状态、关联 task
  ↓
Step 3：对每个未完成 AC 跳到工作流 C
  ↓
Step 4：合并输出"PRD 级改动地图"
  - 按 layer 汇总（domain / infrastructure / application / interfaces / frontend）
  - 列出本 PRD 总影响面
  - 列出关联 SPEC 是否需要 doc-sync
```

### 工作流 C：AC 入口（最精确，其他工作流终将归到这里）

```
用户: /need-to-code ac AC-001-01
  ↓
Step 1：读 AC 元数据
  - Grep "AC-001-01" sprints/backlog/requirements/ → 定位 PRD 文件
  - Read PRD → 解析该 AC 的 BDD、详设引用、依赖、负责人
  - 提取 "> **详设**: SPEC-BE-014 §3.1" → SPEC 路径与章节号
  ↓
Step 2：读 SPEC 对应章节
  - Read docs/specs/.../SPEC-BE-014.md
  - 定位 §3.1 章节
  - 提取章节内的代码块（```python / ```yaml）和反引号标识符
  - 产出"代码实体清单"（同 spec-prelaunch-review Step 1）
  ↓
Step 3：用 GitNexus 把实体清单变成调用链
  - 对每个核心符号调 gitnexus_context({name})
  - 拿到 incoming/outgoing calls + 所属 process flow
  - 汇总相关文件清单（含相对路径）
  ↓
Step 4：反向校验 SPEC ↔ Code
  - 对清单里每个类/方法/字段，Grep/Read 核验是否真实存在
  - 如果有 ≥2 处不一致 → 强烈建议先走 /spec-prelaunch-review
  ↓
Step 5：拉影响面
  - 对清单里"会被修改"的符号，调 gitnexus_impact({direction: "upstream"})
  - 列出 d=1（必破）/ d=2（可能破）依赖
  ↓
Step 6：定位关联 Task
  - Glob sprints/active/**/tasks-*.md
  - Grep "(AC-001-01)" → 看是否已有 task 在做
  - 如有：提示用户"已有 task: tasks-丁昂.md，是否打算继续/接手？"
  - 如无：提示"建议在今日 Wave 创建 task，引用 AC-001-01"
  ↓
Step 7：产出改动地图（见下文格式）
  ↓
Step 8：推荐 next skill
  - SPEC 与代码已偏离 → /spec-prelaunch-review
  - 代码改完准备同步文档 → /doc-sync
  - 准备开 task 写代码 → /sprint-management add-task
```

### 工作流 D：SPEC 入口

```
用户: /need-to-code spec SPEC-BE-014
  ↓
Step 1：读 SPEC frontmatter / 顶部元数据
  - 提取 "> 关联需求: PRD-001-*.md" → 反向找到所有 PRD
  - 提取 "> 所属模块: backend/src/infrastructure" → 锁定主要修改目录
  ↓
Step 2：扫描 SPEC 内的所有 AC 引用
  - Grep "AC-\d{3}[A-Z]?-\d{2}" 当前 SPEC 文件
  - 拿到本 SPEC 关联的 AC 列表
  ↓
Step 3：对每个 AC 跳到工作流 C 的 Step 2-7
  ↓
Step 4：合并输出"SPEC 级改动地图"
```

### 工作流 E：反向（代码入口）

```
用户: /need-to-code from-code backend/src/infrastructure/tools/registry.py:45
  ↓
Step 1：读代码片段，提取关键符号
  - Read 文件指定行的方法/类
  - 提取函数名、所属类、所在模块
  ↓
Step 2：反查 SPEC
  - Grep <类名> docs/specs/**/*.md → 找到所有提及该类的 SPEC
  - Grep <函数名> docs/specs/**/*.md → 进一步精确
  ↓
Step 3：反查 PRD/AC
  - 对找到的每份 SPEC：
    a. Grep 它的文件名 sprints/backlog/requirements/**/PRD-*.md → 找 related_specs 反向引用
    b. Grep "SPEC-BE-014 §X" sprints/backlog/requirements/ → 找 AC 元数据反向引用
  ↓
Step 4：反查 commit 历史
  - git log -L :<symbol>:<file> → 找到引入它的 commit
  - 解析 commit message 中可能引用的 SPEC/PRD/AC 编号
  ↓
Step 5：产出"反向溯源报告"
  - "这段代码属于：PRD-001 / AC-001-01 / SPEC-BE-014 §3.1"
  - "由 commit abc123 在 2026-04-10 引入，作者 丁昂"
  - 如所有反查都为空 → 标记为"孤儿代码"，建议补 PRD 关联或归档
```

### 工作流 F：全量关系图

```
用户: /need-to-code map
  ↓
Step 1：扫描所有 PRD
  - 解析 frontmatter.related_specs
  - 解析每个 AC 的 "> **详设**: SPEC-XXX §Y"
  ↓
Step 2：扫描所有 SPEC
  - 解析顶部 "> 关联需求: PRD-XXX"
  - 提取 SPEC 内代码块的类名、函数、字段
  ↓
Step 3：扫描所有 task
  - 解析 关联需求点 / 关联详设
  - 解析 checkbox 行末的 (AC-XXX)
  ↓
Step 4：调 gitnexus 拿到每个符号的当前位置
  ↓
Step 5：构建关系图谱写入 docs/_index/relation-map.json
  {
    "prd": {
      "PRD-001": {
        "specs": ["SPEC-BE-014", "SPEC-FE-005B"],
        "acs": ["AC-001-01", "AC-001-02", ...]
      }
    },
    "ac": {
      "AC-001-01": {
        "prd": "PRD-001",
        "spec_section": "SPEC-BE-014 §3.1",
        "tasks": ["sprints/active/2026-04-16/wave3-xxx/tasks-丁昂.md"],
        "code_symbols": ["ToolRegistry.register_tool", "..."],
        "files": ["backend/src/infrastructure/tools/registry.py", "..."],
        "status": "🟡"
      }
    },
    "spec": {
      "SPEC-BE-014": {
        "prds": ["PRD-001"],
        "acs": ["AC-001-01", "AC-001-02"],
        "routers": ["backend/src/interfaces/http/agent_router.py"]
      }
    },
    "code_to_doc": {
      "backend/src/infrastructure/tools/registry.py:45": {
        "method": "register_tool",
        "specs": ["SPEC-BE-014 §3.1"],
        "acs": ["AC-001-01"],
        "prds": ["PRD-001"]
      }
    },
    "orphans": {
      "ac_without_code": ["AC-002-03"],
      "code_without_doc": ["backend/src/infrastructure/tools/builtin/unused_tool.py"]
    },
    "generated_at": "2026-04-16T14:32:00+08:00"
  }
  ↓
Step 6：输出统计
  - 总 PRD 数 / AC 覆盖率 / 孤儿代码数 / 孤儿 AC 数
```

---

## 改动地图输出格式（核心产物）

```markdown
# 改动地图 — AC-001-01「工具执行超时控制」

## 1. 需求锚点
- **PRD**: [PRD-001 工具系统增强](sprints/backlog/requirements/PRD-001-*.md)
- **AC**: AC-001-01  `P0`  状态: 🟡 开发中  负责: 丁昂
- **BDD**: 注册工具时设置超时 → 执行超时后自动中断 + 返回错误信息
- **详设**: [SPEC-BE-014 §3.1](docs/specs/.../backend-detail-spec-014-tool-timeout.md#31)

## 2. 关联代码（按 layer 分组）

### domain
| 文件 | 符号 | 当前状态 |
|------|------|---------|
| [engine.py:120](backend/src/domain/agent/engine.py#L120) | `AgentEngine.execute_tool()` | ✅ 已存在 |
| [models.py:45](backend/src/domain/agent/models.py#L45) | `ToolResult.timeout` | ⚠ 需新增 |

### infrastructure
| 文件 | 符号 | 当前状态 |
|------|------|---------|
| [registry.py:45](backend/src/infrastructure/tools/registry.py#L45) | `ToolRegistry.register_tool()` | ✅ 已存在 |
| [base.py:30](backend/src/infrastructure/tools/base.py#L30) | `BaseTool.timeout` | ⚠ 需新增 |

### interfaces
| 文件 | 符号 | 当前状态 |
|------|------|---------|
| [agent_router.py:88](backend/src/interfaces/http/agent_router.py#L88) | `POST /api/v1/agent/execute` | ✅ 已存在 |

### frontend
| 文件 | 符号 | 当前状态 |
|------|------|---------|
| [app.js:1](frontend/static/js/app.js) | 工具状态展示 | ⚠ 需更新 |

## 3. 影响面（gitnexus_impact）

- 直接调用 `ToolRegistry.register_tool` 的位置（d=1，必破）：
  - `AgentEngine.execute_tool` (backend/src/domain/agent/engine.py:60)
  - `ToolFactory.create` (backend/src/infrastructure/tools/factory.py:30)
- 影响 process flow：
  - AgentExecute（5 步）— 第 3 步会受影响
  - ToolRegistration（3 步）— 第 2 步会受影响

## 4. SPEC ↔ Code 一致性
- ✅ `ToolRegistry.register_tool` 签名匹配
- ❌ `BaseTool.timeout` 在代码中不存在 → SPEC v1.0 §3.1 待补真实字段
- ⚠ 建议先走 `/spec-prelaunch-review` 修订 SPEC

## 5. 关联 Task
- 已有 task：[tasks-丁昂.md](sprints/active/2026-04-16/wave3-xxx/tasks-丁昂.md)
  - T1 `[ ]` 实现 ToolTimeout 机制 (AC-001-01) — **未开工**

## 6. 文档同步清单（改完代码要 doc-sync）
- [ ] PRD-001 AC-001-01 状态 ⬜ → 🟡 → ✅（自动由 /prd-status 聚合）
- [ ] SPEC-BE-014 §3.1 补充 `BaseTool.timeout` 真实字段签名

## 7. 推荐下一步
1. **先**：`/spec-prelaunch-review`（SPEC §3.1 有 1 处缺失字段待补）
2. **然后**：开 T1 写代码
3. **最后**：`/doc-sync` 同步 PRD/SPEC
```

---

## 与其他 skill 的边界

| 场景 | 走哪个 skill | 关系 |
|------|------------|------|
| 提需求 → 不知道改哪 | ⭐ `need-to-code` | 入口 |
| 已知 AC，开工前核验 spec ↔ code | `/spec-prelaunch-review` | need-to-code 在 Step 4 引用它 |
| 看 PRD/AC 进度 | `/prd-status` | need-to-code 工作流 B 复用它 |
| 拿到代码改动后做影响面 | `gitnexus-impact-analysis` | need-to-code 在 Step 5 调用它的工具 |
| 探索陌生代码区域 | `gitnexus-exploring` | 比 from-code 更纯代码侧 |
| 改完代码同步文档 | `/doc-sync` | need-to-code 在推荐里指向它 |

**关键区别**：
- `gitnexus-exploring` 是"代码 → 代码"的导航（无需求侧）
- `prd-status` 是"PRD → 进度"的聚合（无代码侧）
- **`need-to-code` 是"PRD ↔ AC ↔ SPEC ↔ Code"的全链路桥梁**，对其他 skill 是**前置入口**而非替代

---

## 硬性约束

- ❌ 本 skill **不写代码、不改文档**，只做定位与建议（防止把"找路"和"动手"混在一起）
- ❌ 反向溯源（from-code）发现孤儿代码时，**不得**自动删除或私自归档（必须报告给 PM）
- ❌ 自然语言入口找到候选 AC 时，**不得**直接进 Step 2，必须让用户确认锚点
- ✅ 所有定位结果必须附"代码实据（文件:行号）"或"文档锚点（文件#章节）"
- ✅ 关系图谱（`/need-to-code map`）落盘到 `docs/_index/relation-map.json`，纳入 git 追踪
- ✅ 关系图谱**不得**手工编辑（任何变更必须通过 `map refresh` 重生成）

---

## 性能与缓存

- 单次 AC 入口（工作流 C）应在 15s 内完成（重在精确，不重在快）
- `/need-to-code map` 全量首跑 2~5 分钟，结果缓存 24h
- `/need-to-code map refresh` 用 git diff 找变更过的 PRD/SPEC/Task/Code，增量更新
- 大 SPEC（>2000 行）切章节读，不要一次性 Read 全文
- 自然语言检索如发现重复输入，应记忆上一次用户的锚点选择

---

## 详细引用规则

具体的 PRD ↔ AC ↔ SPEC ↔ Code 引用语法（在哪个文件什么位置以什么格式写引用、解析时用什么正则）见 [RELATION-MAP.md](RELATION-MAP.md)。

---

## 最小可用版本（MVP）

首版只实现这些命令，其他命令等需要时再加：

1. `/need-to-code ac AC-XXX-YY` — 工作流 C（最高频）
2. `/need-to-code prd PRD-XXX` — 工作流 B
3. `/need-to-code "<自然语言>"` — 工作流 A（依赖现有 grep + LLM 判断，不依赖外部向量库）
4. `/need-to-code from-code <文件:行号>` — 工作流 E
5. `/need-to-code map` — 工作流 F（全量构建，跑得慢但落盘后受益大）

暂缓：`map refresh`（增量）、`orphans`（先靠 map 输出里的 orphans 字段看）。

---

## 自检清单

输出改动地图前 Agent 必须确认：

- [ ] 需求锚点已被用户 approve（自然语言入口）或精确定位（其他入口）
- [ ] 关联代码每条都有"文件:行号"链接（不是只写类名）
- [ ] 影响面列表已调用 `gitnexus_impact`（不是凭印象）
- [ ] SPEC ↔ Code 一致性已验过（不是只看 SPEC 不看代码）
- [ ] 关联 Task 已用 Grep 扫过（不是漏掉别人正在做的）
- [ ] 文档同步清单已列出（不是只写代码改哪）
- [ ] 推荐 next skill 与改动性质匹配
