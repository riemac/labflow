---
name: self-update
description: 对 labflow Codex plugin 本身进行自更新。当某个 skill、prompt、background agent、MCP 配置或 marketplace 入口需要改进时使用。改动通常在新的 Codex session 或插件重载后生效。
---

# labflow Self-Update for Codex

对 labflow plugin 自身进行迭代改进：编辑 `plugins/labflow/` 下的 prompts、agents、skills、MCP 或 manifest → 验证 → 按需提交 → 重新加载 Codex marketplace。

> **关键约束：** 当前 Codex session 不会自动吸收已安装插件内容的变化。改动完成后，重新加载本地 marketplace，并开启新 session 验证。

---

## 可更新的内容

- `plugins/labflow/prompts/*.md`：可手动粘贴的参考 prompt，不是主入口
- `plugins/labflow/agents/*.md`：read-heavy background agents，如 `lab-explore`、`lab-research`
- `plugins/labflow/skills/*/SKILL.md`：skills 的操作指南、模板、规范
- `plugins/labflow/.mcp.json`：插件 MCP 配置
- `plugins/labflow/.codex-plugin/plugin.json`：插件 manifest
- `.agents/plugins/marketplace.json`：本地 marketplace 入口

---

## 更新流程

### 1. 提出并确认改动

用自然中文描述问题和建议改动，获得用户批准后再动手。一次只改一个文件或一个清晰的改动点，除非用户明确要求结构性迁移。

### 2. 编辑文件

修改 `plugins/labflow/` 或 `.agents/plugins/marketplace.json` 下的目标文件。不要在 `main` 重新引入 Copilot-only 结构。

### 3. 按需提交到 git

```bash
cd /home/hac/labflow
git add -A
git commit -m "refactor: <改动一句话描述>

<可选：更详细的理由>"
```

Commit 类型参考：
- `refactor:`：改进现有行为（不是 bug fix）
- `fix:`：修正错误或不一致
- `feat:`：新增 agent/skill/功能

若工作区存在用户未提交改动，先向用户说明，不要把无关变更混进提交。

### 4. 重新加载本地 marketplace

```bash
/home/hac/labflow/plugins/labflow/skills/self-update/scripts/reload_labflow_plugin.sh
```

这里要区分两类 marketplace：

- **本地目录 marketplace**：当前 `labflow` 就属于这一类。经验上要把“刷新”当成
  `remove` 再 `add`，不要只执行 `add`，也不要误用 `upgrade`。
- **Git marketplace**：若 Codex CLI 明确把它识别为 Git marketplace，再使用
  `codex plugin marketplace upgrade ...`。

`codex plugin marketplace add /home/hac/labflow` 在 marketplace 已存在时，很多时候只会报告
“already added”，并不可靠地表达“刷新完成”。因此本地目录源默认走 `remove -> add`。

### 5. 告知用户

说明改动内容、验证结果，以及**需要开新 Codex session 才能完整观察行为变化**。

---

## 原则

- **最小改动**：每次只改一个清晰的问题，不做大范围重构
- **改后验证**：下次使用时观察改动是否达到预期，再决定是否继续迭代
- **不破坏已有结构**：修改前先读完整文件，理解上下文
- **不替用户做决定**：涉及行为变更的先说明取舍；明显的 typo/措辞优化可直接改
- **skill-first**：优先沉淀稳定重复动作，不把未用顺的科研工作流提前制度化
