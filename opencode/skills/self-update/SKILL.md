---
name: self-update
description: 对 labflow 的 opencode 集成本身进行自更新。当某个 skill、agent、全局规则、install 脚本或 opencode 配置需要改进时使用。改动需重新部署到 ~/.config/opencode 并重启 opencode 后生效。
---

# labflow Self-Update for opencode

对 labflow 的 opencode 集成做迭代改进：编辑 `opencode/` 下的
agents、skills、规则或 install 脚本 → 验证 → 按需提交 → 重新部署 → 重启 opencode。

> **关键约束：** opencode 只在启动时加载一次配置/skills/agents/规则，不热重载。
> 改动完成后，重新运行 install 脚本部署到 `~/.config/opencode`，并提示用户**退出
> 并重启 opencode** 才能观察行为变化。

---

## 可更新的内容

- `opencode/agents/*.md`：primary / subagent 定义
- `opencode/skills/*/SKILL.md`：skills 的操作指南、模板、规范
- `opencode/labflow-rules.md`：全局跨 agent 规则
- `opencode/install.sh`：部署脚本
- 用户的 `~/.config/opencode/opencode.json`：instructions / mcp / agent 注册

> Codex 侧的内容（`.codex-plugin/`、`hooks/`、`.mcp.json`、marketplace）属于
> `main` 分支，不在 opencode 集成的自更新范围内。

---

## 更新流程

### 1. 提出并确认改动

用自然中文描述问题和建议改动，获得用户批准后再动手。一次只改一个文件或一个清晰的
改动点，除非用户明确要求结构性迁移。

### 2. 编辑文件

修改 `opencode/` 下的目标文件。SKILL.md frontmatter 只认
`name` / `description`（及可选 `license` / `compatibility` / `metadata`）；
agent frontmatter 用 `description` / `mode` / `permission` 等字段，正文即 prompt。

### 3. 按需提交到 git

```bash
cd /home/hac/labflow
git add -A
git commit -m "refactor: <改动一句话描述>"
```

Commit 类型：`refactor:` 改进现有行为，`fix:` 修正错误，`feat:` 新增 agent/skill。
若工作区存在用户未提交改动，先说明，不要把无关变更混进提交。

### 4. 重新部署到 opencode

```bash
/home/hac/labflow/opencode/install.sh
```

脚本把 agents / skills / 规则同步到 `~/.config/opencode/`。

### 5. 告知用户

说明改动内容、验证结果，以及**需要退出并重启 opencode 才能观察行为变化**。

---

## 原则

- **最小改动**：每次只改一个清晰的问题，不做大范围重构
- **改后验证**：下次使用时观察改动是否达到预期，再决定是否继续迭代
- **不破坏已有结构**：修改前先读完整文件，理解上下文
- **不替用户做决定**：涉及行为变更的先说明取舍；明显的 typo/措辞优化可直接改
- **skill-first**：优先沉淀稳定重复动作，不把未用顺的科研工作流提前制度化
