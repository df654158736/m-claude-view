# Sprint 任务交付验收规范（所有任务默认适用）

> **适用范围**：`sprints/active/**/tasks-*.md` 所有任务文件
> **使用方式**：任务文件末尾加一句 `本任务适用 [交付验收规范](../../_templates/ACCEPTANCE-CRITERIA.md)` 即可默认生效；如有偏离在任务文件内显式覆盖。
> **目标**：确保 Agent / 开发者交付的代码经过完整测试链路，交付即可直接合并。

---

## 1. 测试分层定义

每份任务必须覆盖以下层级（按任务复杂度按需选用，但**单元测试**为底线）：

| 层级 | 用途 | 典型命令 | 强制性 |
|------|------|---------|--------|
| **单元测试** (Unit) | 方法 / 类级别，mock 外部依赖 | `PYTHONPATH=backend pytest backend/tests/test_xxx.py -v` | 🔴 必选 |
| **集成测试** (Integration) | 真实依赖，覆盖 I/O 路径 | 同上，区分 tag 或目录 | 🟡 凡涉及外部系统必选 |
| **端到端测试** (E2E) | 完整业务链路 | HTTP API → Agent → Tool → 结果 | 🟡 涉及跨层链路必选 |
| **回归测试** (Regression) | 已有测试全绿，无破坏 | `PYTHONPATH=backend pytest backend/tests/ -v` | 🔴 合并前必跑 |

---

## 2. 覆盖率门槛

| 维度 | Python |
|------|--------|
| 行覆盖率 (Line) | ≥ 80% |
| 分支覆盖率 (Branch) | ≥ 70% |
| 新增代码 | ≥ 90%（严于整体） |
| 核心 / 关键类 | ≥ 90%（如 ReAct Engine、ToolRegistry） |

**禁止**：
- ❌ 通过 `skip` / 删除测试让门禁通过
- ❌ 用 `assert True` 式的空测试凑数
- ❌ 只测 happy path 不测异常路径

---

## 3. 可观测性验证

凡任务涉及新增事件类型 / 日志字段 / Packet 格式：

- [ ] **事件格式**：新 packet type 符合 `logs/packets.jsonl` 现有约定
- [ ] **结构化日志**：关键事件 JSON 字段命名符合现有约定
- [ ] **Dashboard**：新事件类型在 Web Dashboard 正确渲染

---

## 4. 配置与回滚验证

凡任务涉及新增配置项 / 环境变量：

- [ ] **默认值下启动**：不设任何新配置时，服务行为与改动前一致（向后兼容）
- [ ] **非法配置**：启动时 fail-fast + 错误信息清晰
- [ ] **回滚路径**：明确"如何回到改动前状态"的步骤

---

## 5. 接口契约稳定性

凡任务涉及 REST API 变更：

- [ ] **破坏性变更**：显式标注 "Breaking Change" 并列出影响范围
- [ ] **前端兼容**：前端 `app.js` 调用逻辑同步更新
- [ ] **测试覆盖**：改 API 必改对应测试

---

## 6. PR 描述模板

```markdown
## 变更摘要
- 一句话描述本次变更解决的问题 / 实现的能力
- 关联 OpenSpec 提案 / 需求文档链接

## 主要改动
- 模块 1：改动点
- 模块 2：改动点

## 测试证据
- [ ] 单元测试：`pytest backend/tests/` 通过 ({N} 个新增 / {M} 个修改)
- [ ] 覆盖率：行 {X}% / 分支 {Y}%（新增代码）
- 关键截图 / 日志片段

## 回滚方案
- 如何回到改动前状态

## 文档同步
- [ ] 需求文档（PRD）
- [ ] 详设文档（SPEC / OpenSpec）
- [ ] PROGRESS.md
- [ ] 任务状态（tasks-{gitid}.md）
```

---

## 7. Definition of Done（合并前复核）

每项必须勾选，未勾选不允许合 PR：

- [ ] ① 所有任务 T1~Tn 验收 ✅
- [ ] ② `PYTHONPATH=backend pytest backend/tests/ -v` 全绿
- [ ] ③ `pyright` 类型检查通过
- [ ] ④ 新增 / 修改代码覆盖率达标（§2）
- [ ] ⑤ 可观测性验证通过（§3）
- [ ] ⑥ 配置默认值启动行为不变（§4）
- [ ] ⑦ 文档同步走过 `/doc-sync` 或 `/doc-sync-after-dev`
- [ ] ⑧ PR 描述按 §6 模板填写
- [ ] ⑨ `PROGRESS.md` + 任务文件状态更新（`⬜` → `✅`）

---

## 8. 测试相关反模式（禁止）

| 反模式 | 为什么禁止 |
|-------|----------|
| `@pytest.mark.skip` 临时跳过 | 掩盖问题，累积技术债 |
| 空 except `except: pass` | 吞异常，让测试误通过 |
| `assert True` / 无断言测试 | 凑覆盖率，无业务验证 |
| mock 内部逻辑而非外部依赖 | 绕过真实行为 |
| 删除失败测试让 CI 通过 | 最严重反模式，**直接红线** |
| 测试依赖外网 / 生产环境 | 不可重现、破坏 CI 隔离 |

---

## 9. 特殊场景要求

### 9.1 涉及 LLM 调用

- 大模型调用走 mock / 录制回放，不打真实 LLM API
- 固定 temperature=0 或 mock 确定性输出，结果可重现
- 断言结构（返回了 tool_call / 返回了 final answer），不断言自然语言内容

### 9.2 涉及 MCP 工具

- 使用 `fake_mcp_server.py` 或类似 mock
- 覆盖连接失败、超时、异常返回
- 延迟加载路径：未加载 → 首次调用 → 已加载

### 9.3 涉及文件操作

- 使用 `tmp_path` fixture，不操作真实文件系统
- 覆盖：文件不存在、权限不足、大文件

---

## 附录 · 快速索引

- [CLAUDE.md 质量门](../../CLAUDE.md) — 项目级红线
- [sprint-management skill](../../.claude/skills/sprint-management/SKILL.md) — Sprint 创建规范
- [git-workflow skill](../../.claude/skills/git-workflow/SKILL.md) — 分支 / 提交 / PR
- [doc-sync-after-dev skill](../../.claude/skills/doc-sync-after-dev/SKILL.md) — 合并前文档同步
