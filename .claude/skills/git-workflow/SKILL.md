---
name: git-workflow
description: m-claude-view Git 工作流：分支管理、提交规范、PR 流程。
trigger: 用户提到"git"、"提交"、"commit"、"push"、"分支"、"branch"、"PR"
---

# Git 工作流

## 提交三步曲

**每次 commit + push 必须按顺序：**

```bash
# Step 1: 先拉取远程最新代码
git pull --rebase origin <当前分支>

# Step 2: 提交本地变更
git add <files>
git commit -m "<前缀>: <描述>"

# Step 3: 推送到远程
git push origin <当前分支>
```

> 不 pull 直接 push → rejected（non-fast-forward）
> 禁止 `git push --force`

---

## Commit Message 格式

### GitHub（默认）

Conventional Commits：`feat:` / `fix:` / `refactor:` / `chore:` / `test:` / `docs:`

### GitLab（公司仓库推送时使用中文前缀）

| 前缀 | 用途 | 示例 |
|------|------|------|
| `更新:` | 更新现有功能/文档 | `更新: ReAct 循环迭代策略优化` |
| `修复:` | 修复 Bug | `修复: MCP 工具延迟加载超时` |
| `增加:` | 新增功能/文件 | `增加: 文件上传工具` |
| `删除:` | 删除文件/功能 | `删除: 过期的临时文档` |
| `临时:` | WIP 临时提交 | `临时: 保存工具策略引擎进度` |
| `测试:` | 测试相关 | `测试: 添加 ToolRegistry 单元测试` |
| `恢复:` | 回退/恢复 | `恢复: 回退配置变更` |
| `合并:` | 合并分支 | `合并: 合并 master 到 feature 分支` |

---

## 分支策略

```
master (主干分支)
├── feature/{module}-{task}     ← 功能开发
├── chore/{description}         ← 配置/文档/依赖变更
├── release/v{version}          ← Release 准备
└── hotfix/{description}        ← 紧急修复
```

### 创建功能分支

```bash
git checkout master
git pull origin master
git checkout -b feature/{module}-{task-name}
```

---

## PR 创建规范

```bash
git push origin feature/{module}-{task-name}

gh pr create \
  --base master \
  --head feature/{module}-{task-name} \
  --title "feat: 实现工具策略引擎" \
  --body "$(cat <<'EOF'
## Summary
- 实现 ToolPolicy 策略引擎
- 添加工具执行前拦截

## Testing
- Unit tests: ✅
- Integration tests: ✅

## Checklist
- [x] 代码符合项目规范
- [x] PROGRESS.md 已更新
- [x] 文档已同步
EOF
)"
```

---

## 每天开始工作

```bash
git checkout master
git pull origin master
git checkout feature/{module}-{task}
git rebase master
```

---

## 冲突解决

```bash
git rebase origin/master
# CONFLICT → 编辑文件解决
git add <resolved-files>
git rebase --continue
```
