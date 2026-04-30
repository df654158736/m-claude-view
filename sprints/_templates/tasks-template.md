# Tasks — {git-user} — {YYYY-MM-DD} Wave{N} {Wave Name}

> **Sprint**: {YYYY-MM-DD} / Wave {N}
> **Focus**: {一句话描述本 Wave 要解决的核心问题 / 交付的核心能力}
> **模块**: {domain / application / infrastructure / interfaces / frontend}
> **分支**: `feature/{module}-{task-slug}`
> **需求来源**: {评审日期 / 决策人 / 触发背景}
> **设计依据**:
> - [OpenSpec 提案](../../../../openspec/changes/xxx/proposal.md)
> - [详设文档](../../../../docs/specs/xxx.md)
> **预估总工时**: {X} 人日
> **分配人**: {gitid}
> **本任务适用** [交付验收规范](../../_templates/ACCEPTANCE-CRITERIA.md)

---

## ⚠️ 开工前必读（现状核对）

> **目的**：新人/Agent 接手时，先把"容易误读的现状"写清楚，避免 PR 才发现踩坑。

1. **{现状点 1}**
   - 现状：{一句话描述代码现况}
   - 影响：{为什么要特别注意}
   - 你要做：{正确的做法}

2. **{现状点 2}** ...

---

## 需求背景

{2-3 段，描述为什么要做这个 Wave、不做的话会怎样、评审上拍过的关键决策。避免堆砌，聚焦"背景 + 约束"。}

---

## 范围边界

- ✅ 本 Wave 做：{明确在做的事，按输出物维度列}
- ❌ 本 Wave 不做：{显式排除，避免范围蔓延}
- ⚠️ 前置依赖：{上游 Wave / 他人任务 / 必须先合的 PR}

---

## 任务清单

### T1 · {任务名} ⬜ ({X}d)

**目标**：{一句话说清要达成什么}

**交付物**：
- [ ] 代码：{文件 / 类 / 方法清单}
- [ ] 测试：{新增测试文件}
- [ ] 文档：{如需更新哪份文档}

**验收**（每项必须可验证）：
- [ ] `PYTHONPATH=backend pytest backend/tests/test_xxx.py -v` 全绿（≥ {N} 用例）
- [ ] 本地跑通 {场景 A} → {预期输出}
- [ ] 本地跑通 {场景 B 异常路径} → {预期错误消息}

---

### T2 · {任务名} ⬜ ({X}d)

**目标**：...

**交付物**：
- [ ] ...

**验收**：
- [ ] ...

---

<!-- 根据 Wave 大小增减 T3~Tn，单个任务 > 1.5 人日建议再拆 -->

---

## 技术红线自查（照搬 CLAUDE.md，勾掉不涉及项）

- [ ] ✅ domain/ 不依赖 infrastructure/ 或 interfaces/
- [ ] ✅ 不绕过 ToolRegistry 直接调用工具
- [ ] ✅ API Key 不写入代码或配置文件
- [ ] ✅ 没有空 catch 块 / 跳过测试
- [ ] ✅ 不提交 .env / API Key / 大文件

---

## 合并前 Checklist

- [ ] 所有 T1~Tn ✅
- [ ] `PYTHONPATH=backend pytest backend/tests/ -v` 全绿
- [ ] `pyright` 类型检查通过
- [ ] 文档同步（`/doc-sync` 或 `/doc-sync-after-dev`）
- [ ] `PROGRESS.md` + 本文件状态更新（`⬜` → `✅`）

---

## Wave 级风险 / 遗留

- {已识别风险 + 缓解措施}
- {本 Wave 未覆盖但需下一 Wave / backlog 跟进的项}
