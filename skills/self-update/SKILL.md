---
name: self-update
description: 对 labflow plugin 本身进行自更新。当你发现某个 skill/agent 需要改进、某条规则需要调整，或用户反馈使用体验问题时使用。改动会在下次 session 生效。
---

# labflow Self-Update

对 labflow plugin 自身进行迭代改进：编辑 agents 或 skills → 提交 → 重装插件。

> **关键约束：** 修改后需重装插件（`copilot plugin install ~/labflow`），改动**下次 session 才生效**，当前 session 不会感知变更。

---

## 可更新的内容

- `~/labflow/agents/*.agent.md`：agent 的行为逻辑、prompt 结构、工作流
- `~/labflow/skills/*/SKILL.md`：skill 的操作指南、模板、规范

---

## 更新流程

### 1. 提出并确认改动

用 `ask_user` 描述问题和建议改动，获得用户批准后再动手。一次只改一个文件或一个清晰的改动点。

### 2. 编辑文件

直接用 `edit` 工具修改 `~/labflow/agents/` 或 `~/labflow/skills/` 下的目标文件。

### 3. 提交到 git

```bash
cd ~/labflow
git add -A
git commit -m "refactor: <改动一句话描述>

<可选：更详细的理由>"
```

Commit 类型参考：
- `refactor:`：改进现有行为（不是 bug fix）
- `fix:`：修正错误或不一致
- `feat:`：新增 agent/skill/功能

### 4. 重装插件更新缓存

```bash
copilot plugin install ~/labflow
```

输出 `Plugin "labflow" installed successfully.` 即成功。

### 5. 告知用户

说明改动内容，以及**需要开新 session 才能生效**。

---

## 原则

- **最小改动**：每次只改一个清晰的问题，不做大范围重构
- **改后验证**：下次使用时观察改动是否达到预期，再决定是否继续迭代
- **不破坏已有结构**：修改前先读完整文件，理解上下文
- **不替用户做决定**：涉及行为变更的 → 先 ask_user；明显的 typo/措辞优化 → 可直接改
