---
name: spec-prelaunch-review
description: |
  Sprint 任务开工前的全链路代码核验 — 用户说"开始开发我的 sprint 任务"时，
  Agent 必须先读任务文件里引用的 spec，把 spec 中所有"代码实体引用"（类名、方法签名、
  字段名、枚举值、Pydantic Model、状态机档位）与真实代码逐项比对，输出落地障碍清单与 spec 修订建议，
  避免按纸面方案开工后在运行时连续踩坑。
  AUTO-TRIGGER：用户说"开始开发我的 sprint 任务"、"开始开发 wave X 任务"、"继续昨天的 sprint"、
  "按这份 spec 开工"、"评审一下 spec XXX"，或 Agent 读新 spec/任务文件时发现 ≥2 处代码引用
  与真实代码不符。
user-invocable: true
---

# /spec-prelaunch-review — 详设开工前全链路核验

## 何时触发

### 主场景（最常见）：Sprint 任务开工

用户说下列任一话术，Agent 不得直接动手写 T1 实现代码，必须先走本 skill：

- "开始开发我的 sprint 任务"
- "开始开发 wave{N} 任务" / "开始 wave{N} 的 T1"
- "继续昨天/之前的 sprint 任务"（如之前未走过本 skill）
- "按这份任务开工" / "我来做这个任务"

**Sprint 开工标准入口流程**：

```
用户: "开始开发我的 sprint 任务"
  ↓
Step A: Agent 定位任务文件
        读 sprints/active/{today}/wave{N}-*/tasks-{gitid}.md
        （gitid = git config user.name 去空格+小写）
  ↓
Step B: Agent 从任务文件里提取 spec 引用
        找"任务主依据" / "依赖文档" / "SPEC-" 等关键词下列出的 docs/specs/** 路径
  ↓
Step C: Agent 对每份引用的 spec 跑本 skill 的 Step 1-6
  ↓
Step D: 产出"开工结论"给用户 approve
  ↓
Step E: Approve 后才开 T1
```

**为什么在 Sprint 开工处拦截而不是在 spec 刚写完时**：
因为 spec 作者写 spec 时不一定在看代码现场（可能是设计评审、需求讨论产出的），
真正"按 spec 写代码"的人（可能是另一个同事 / 另一个 Claude 会话）才有动力做全链路核验。
把核验点放在开工瞬间，能最大程度暴露"纸面 → 代码"的偏差。

### 其他触发场景

1. 用户分配了一份详设文档（`docs/specs/**`），要求"按这份开工"、"这份能做吗"
2. 用户明确说"评审一下 spec"、"开工前对一下代码"、"自查一下"
3. Agent 在阅读 spec 或 tasks 文件时发现 ≥2 处"spec 描述与真实代码不一致"（方法签名、字段名、Model 结构等）
4. Spec 是另一个 Agent/人产出的，本会话 Agent 将是实际执行者（跨人 / 跨会话交接）
5. Spec 的"接口/数据模型"章节里出现了具体类名、方法名、字段名（说明有可核验的代码引用）

### 不触发的场景（避免误用）

- 用户只是问 spec 的问题、不准备写代码 → 直接答
- 任务是纯 bug 修复 / 样式调整 / 文案修改，没有关联 spec → 跳过
- 任务文件里没有引用 `docs/specs/**`（例如纯运维任务、纯文档任务） → 跳过
- 用户已经开始写代码、并且本会话之前已经跑过本 skill → 跳过（不重复核验）

## 本 skill 存在的原因（必读）

**历史案例**：一份看似"详细到可以直接照抄"的详设，拿到真实代码一比对，可能暴露多处落地障碍——

- `ToolRegistry.execute()` 签名记错（少写参数）
- `AgentTask.task_id` 是必填字段，spec 却要求在 task_id 生成之前先建关联记录
- Pydantic Model 字段名和 spec 里写的全不对
- 某个类根本没有 spec 依赖的属性
- 状态机档位跳跃，会踩回退逻辑
- 等等

**结论**：spec 写得再细，也只是作者头脑中对代码的印象。没经过"全链路代码比对"就开工 = 用运行时当 PR reviewer = 工时翻倍。

**本 skill 的价值**：把这种隐性的、依赖个人经验的"自查"动作显式化、流程化，让团队每个人（不只是高级工程师）都能在开工前 0.5 天抓住所有运行时级障碍。

---

## 硬性约束

- ❌ 未经本 skill 核验，不得按 spec 写实现代码（测试、PoC 脚本可以写）
- ❌ 不得仅凭 spec 里的类名/方法名写代码（必须 Grep/Read 验过真实存在）
- ❌ 发现落地障碍不得"绕着写"或"私自改 spec 字段名让代码对得上"——必须反馈给 spec 作者
- ✅ 核验范围覆盖 spec 全文提及的所有代码实体，不得只抽样
- ✅ 核验结论必须附代码实据（文件路径 + 行号），不得凭"我觉得"
- ✅ 发现重大偏差（≥3 处编译级障碍）必须触发 spec 版本升级（v0.x → v0.y），不得在 v0.x 内打补丁

---

## 标准流程（Agent 必须按序执行）

### Step 1：提取 spec 的"代码实体引用清单"

通读 spec 全文，把所有**具体的代码引用**提取成清单。这些是本次核验的"被告"：

| 引用类型 | 提取什么 | 举例 |
|---------|---------|-----|
| **类 / 方法** | 类名 + 方法名 + 签名（参数、返回值） | `ToolRegistry.execute(tool_name: str, args: dict) -> str` |
| **Pydantic Model** | 类名 + 字段清单（名称、类型、约束） | `AgentTask { task_id: str, status: TaskStatus, result: Optional[str] }` |
| **REST 端点** | method + path + 请求/响应 schema | `POST /api/ask` → `{"question": str}` |
| **枚举值 / 状态机** | 枚举类名 + 所有档位 + 转换规则 | `TaskStatus { PENDING → RUNNING → COMPLETED / FAILED }` |
| **配置项** | 配置 key + 默认值 + 所属文件 | `llm.max_iterations=20` in `config.yaml` |

> 提取方式：Grep spec 文件里的代码块（```python / ```yaml）+ 扫正文里被反引号包住的标识符。
> 产物：写到临时清单（可以是对话内的 markdown 表格，不需要建文件）。

### Step 2：逐项代码核验

对 Step 1 清单的每一条，用 `Grep` / `Read` / `Glob` 核验**是否真实存在 + 签名/字段是否匹配**。

**核验规则**：

- **类 / 方法**：Grep 类名定位文件 → Read 定位方法 → 对比签名。方法参数数量、顺序、类型必须逐项匹配；返回类型必须匹配。
- **Pydantic Model 字段**：Read Model 类 → 比对字段名、类型、`Field()` 约束（`default`、`min_length`、`Optional` 等）。Spec 里出现但 Model 没有的字段必须标为障碍。
- **REST 端点**：Read FastAPI Router 文件 → 比对端点 path、method、请求/响应 schema。确认路由是否真的注册了。
- **枚举 / 状态机**：Read 枚举类 → 列出所有真实档位；Grep 使用该枚举的 `if` / `match` 分支，找出已有的"状态转换"逻辑，看 spec 的新转换路径是否会与现有逻辑冲突。
- **配置项**：Read `config.yaml` 和 `settings.py` → 确认 key 存在、默认值是否一致。

**分类障碍等级**：

| 等级 | 含义 | 判定标准 |
|------|------|---------|
| **编译级** | 按 spec 写必然报错 | 方法签名错、类名错、字段名错、返回类型错 |
| **运行时级** | 语法过但运行时抛异常 | 违反 Pydantic 必填字段、枚举值不存在、类型不匹配导致 ValidationError |
| **数据一致性级** | 不抛异常但数据错 | 状态机跳跃破坏回退逻辑、字段默认值不符合 spec 预期 |
| **架构设计级** | 能跑但违反项目规范 | 违反依赖方向（domain 依赖 infrastructure）、单一职责破坏 |
| **契约一致性级** | API 层与内部层不齐 | Spec 要求的字段在 Pydantic Model 有但 FastAPI 端点没暴露 |

### Step 3：产出"落地障碍清单"

格式固定如下（便于 spec 作者追踪修订点）：

| # | 等级 | spec 位置 | spec 描述（摘录） | 代码实据 | 核验结论 |
|---|------|----------|------------------|---------|---------|
| 1 | 编译级 | §3.2 Step 4 | `registry.execute(tool_name)` | `registry.py:45-48` 实际签名 3 参 | spec 调用会报错 |
| 2 | 运行时级 | §4.1 数据模型 | 在 task_id 生成前创建 AgentTask | `models.py:20 task_id: str` 必填 | Pydantic ValidationError |
| 3 | 架构设计级 | §3.3 | 向 AgentEngine 注入 StorageRepo + ConfigLoader | `engine.py:30-45` 当前仅依赖 LLM client | 违反 domain 层依赖规则 |

每一行必须有**代码实据（文件:行号）**，不得只写"感觉不对"。

### Step 4：识别"关键决策分歧"

有些问题不是"对错"，而是"设计取舍"——需要让 spec 作者（或评审人）决策而不是 Agent 自己选。标准问题形态：

> **Q{N}**：关于 {主题}，v{spec 版本} 选择了 A 方案（{一句话概述}），但从 {某角度} 看 B 方案（{一句话概述}）更合适。
> - A 方案代价：{具体代价}
> - B 方案代价：{具体代价}
> - Agent 推荐：{A/B/待决策} + {一句话理由}

典型决策分歧：

- **失败路径策略**：工具执行失败要不要阻塞 ReAct 循环？
- **状态机选择**：用现有 TaskStatus 枚举 vs. 新建局部枚举？
- **依赖注入层级**：把新职责塞进现有 Engine vs. 新建 Service？
- **重试策略**：工具超时后重试还是直接失败？
- **配置粒度**：全局配置 vs. 工具级配置？

### Step 5：产出 spec 修订方向

**不要直接改 spec**，而是给 spec 作者一份"修订点清单"，方便他/她自己走 doc-sync：

```markdown
## Spec 修订方向（发给 spec 作者）

### 必改项（对应 Step 3 的障碍清单）
- [ ] §3.2 Step 4：修正 `execute` 签名为 3 参
- [ ] §4.1 数据模型：AgentTask 创建时机改为 `task_id` 已就绪之后
- [ ] ...

### 待决策项（对应 Step 4 的 Q1-QN）
- [ ] Q1：Engine 依赖是否扩展？Agent 推荐不扩展
- [ ] Q2：工具执行失败是否阻塞循环？Agent 推荐不阻塞但必须记录日志
- [ ] ...

### 建议版本跃迁
当前 v0.3 → 修订后 v0.4（理由：{重大偏差 / 设计分歧}）
```

### Step 6：决定开工门槛

基于 Step 3 + Step 4，给出明确的开工结论：

| 结论 | 适用情况 | 下一步 |
|------|---------|-------|
| 🟢 **直接开工** | 0 处编译级 + 0 处运行时级障碍 + 无关键决策分歧 | Agent 按 spec 原样执行 |
| 🟡 **spec 微调后开工** | ≤2 处编译级 + 已有明确修复路径 | spec 作者小改后即可开 T1 |
| 🟠 **spec 版本升级后开工** | ≥3 处编译级 或 ≥1 处架构设计级 或 ≥2 处待决策 | spec 版本 +1 走 doc-sync，用户 approve 后开工 |
| 🔴 **需要重做设计** | 方案根基错误（例如 domain 层直接依赖 infrastructure） | 发回 spec 作者重写对应章节 |

## 最小核验样例

以工具策略引擎 spec 为例，展示一次完整的"Spec 描述 → 代码实据 → 障碍结论"核验链：

````markdown
**Spec 引用**（v1 §3.3）：
> 为 AgentEngine 注入 ToolPolicyService 和 PacketLogRepo，
> 在 execute_tool() 完成后持久化执行记录到 PacketLog

**Grep 与 Read**：
```
Grep: "class AgentEngine" → engine.py:15
Read engine.py:30-45 →
  构造函数签名：(llm_client: OpenAIClient, tool_registry: ToolRegistry)
```

**核验结论**：
- 当前仅依赖 LLM client 和 ToolRegistry，纯编排角色
- Spec 要求新增 2 个依赖（PolicyService + LogRepo），职责从"编排"扩展为"编排 + 策略 + 持久化"
- 等级：架构设计级（违反 domain 层依赖方向）
- Agent 推荐：把持久化下沉到 application 层的 use case，Engine 零改动
````

## 产出物

本 skill 的标准产出：

1. **落地障碍清单**（Step 3 表格） — 必产出
2. **关键决策分歧清单**（Step 4 Q1-QN） — 如有则产出
3. **Spec 修订方向清单**（Step 5） — 必产出
4. **开工结论**（Step 6） — 必产出

可选产出（重大评审才需要）：

5. **评审结论文档** — 放到 `tests/{gitid}/` 或 `sprints/active/{date}/{wave}/coordination.md`

## 与其他 skill 的关系

| 场景 | 走哪个 skill |
|------|------------|
| **拿到 spec、还没写代码** | ⭐ 本 skill（spec-prelaunch-review） |
| 代码写完了、合并前自查 | `/code-review` |
| 代码与文档不一致需要同步 | `/doc-sync` / `/doc-sync-after-dev` |
| 写一份新的详设文档 | 直接在 `docs/specs/` 下编写 |

关键区别：`code-review` 看的是"**写完的代码**"，本 skill 看的是"**还没开工的 spec**"。前者防止 bad code 合进主干，后者防止 bad spec 浪费 Sprint 工时。

## 常见误用

- ❌ **只挑"可能有问题"的几处核验** → 必须覆盖 spec 全文的代码引用清单
- ❌ **发现障碍就私下改 spec 字段名** → 必须反馈给 spec 作者，走 doc-sync
- ❌ **没有代码实据就下判断**（"我觉得这个方法不存在"）→ 必须 Grep/Read 出文件:行号
- ❌ **把"设计分歧"当"障碍"处理** → 设计分歧是 Q 问题，需要决策者答；障碍是事实错误
- ❌ **核验完就开工，不给 spec 作者看清单** → 必须把清单发给 spec 作者 approve 后再开工

## Checklist（Agent 自检）

开工前确认以下全部 ✅：

- [ ] Step 1 代码实体清单已完整提取（没有遗漏 spec 中用反引号/代码块标注的标识符）
- [ ] Step 2 每条实体都有 Grep/Read 核验记录（不是只核验几条）
- [ ] Step 3 每条障碍都有文件:行号形式的代码实据
- [ ] Step 4 所有"设计取舍"都被识别为 Q 问题，而不是偷偷自行选择
- [ ] Step 5 修订清单已发给 spec 作者
- [ ] Step 6 开工结论已产出，且用户 approve
- [ ] 如果有 ≥3 处编译级障碍，spec 版本已升级（v0.x → v0.y）
