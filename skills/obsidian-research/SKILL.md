---
name: obsidian-research
description: 科研知识管理技能。使用 Obsidian CLI 读写科研 vault，管理研究语境（_context.md）、工程进展（_progress.md）和 idea 体系（ideas/）。在科研对话开始、记录发现、更新进展时使用。
---

# Obsidian 科研知识管理

使用 Obsidian CLI（`obsidian`）读写科研 vault，替代 `/memories/` 私有文件。

> 前提：需要 Obsidian 应用正在运行，且 vault 已打开。

---

## Vault 结构约定

每个科研项目对应一个 vault：

```
vault root/
├── _context.md            ← 研究语境快照（每次对话必读，≤1页，覆写）
├── _progress.md           ← 当前任务状态（每次对话必读，≤1页，覆写）
├── _progress-history.md   ← changelog（追加，agent 启动不读，人工参考）
├── ideas/
│   ├── _map.md       ← MOC 总图（idea 讨论模式时读写）
│   ├── h-*.md        ← hypothesis（待验证方案/解释）
│   ├── q-*.md        ← question（未解决问题）
│   ├── f-*.md        ← finding（已确认实验结论）
│   └── d-*.md        ← decision（收敛的架构/方法选择）
└── tasks/
    └── task-*.md     ← 任务 brief（LabPrompt 写入，人工导航层）
```

Atom 笔记（h/q/f/d）的 frontmatter：

```yaml
---
type: hypothesis        # hypothesis | question | finding | decision
status: active          # active | resolved | abandoned
confidence: 0.7         # 0.0-1.0，用于 hypothesis 和 finding
tags: [type/hypothesis, status/active]
related: ["[[h-other]]", "[[f-result-x]]"]
---
```

---

## 核心操作

### 0. 每次对话开始：读取研究语境

```bash
obsidian vault="Research" read file="_context"
obsidian vault="Research" read file="_progress"
```

### 1. 更新工程进展

```bash
# 追加进展记录
obsidian vault="Research" append file="_progress" content="\n## $(date +%Y-%m-%d)\n- 完成了 X\n- 下一步：Y"

# 更新语境快照（整个文件替换时先删除再创建，或用 append 追加补丁）
obsidian vault="Research" append file="_context" content="\n> **更新 $(date +%Y-%m-%d)**：当前焦点已转移到 X"
```

### 2. 记录新发现（finding）

```bash
# 创建 finding atom
obsidian vault="Research" create \
  name="ideas/f-reward-shaping-matters" \
  content="---\ntype: finding\nstatus: active\nconfidence: 0.85\ntags: [type/finding, status/active]\nrelated: [\"[[h-dense-reward]]\"]\n---\n\n# Dense reward 显著提升早期收敛速度\n\n实验配置：SAC + IsaacGym，sparse vs dense reward 对比。\n\n**结论**：dense reward 在前 5M steps 样本效率提升 3x，但最终性能持平。\n\n[[h-dense-reward]] 假设部分成立。" \
  silent

# 更新 _map.md 链接
obsidian vault="Research" append file="ideas/_map" content="\n- [[f-reward-shaping-matters]]：dense reward 早期样本效率 3x，最终持平"
```

### 3. 记录新假设（hypothesis）

```bash
obsidian vault="Research" create \
  name="ideas/h-proprio-beats-visual" \
  content="---\ntype: hypothesis\nstatus: active\nconfidence: 0.6\ntags: [type/hypothesis, status/active]\n---\n\n# proprio obs 在接触密集任务上优于 visual obs\n\n动机：视觉 obs 存在 sim2real gap，proprio 更鲁棒。\n\n待验证：在 dexterous manipulation benchmark 上对比。" \
  silent
```

### 4. 标记问题为已解决

```bash
obsidian vault="Research" property:set name="status" value="resolved" file="ideas/q-sim2real-gap"
```

### 5. 搜索相关笔记

```bash
# 查找所有活跃假设
obsidian vault="Research" search query="#type/hypothesis #status/active"

# 查找与 reward 相关的笔记
obsidian vault="Research" search query="reward" path="ideas"

# 查看某笔记的反向链接
obsidian vault="Research" backlinks file="ideas/h-dense-reward"
```

### 6. idea 讨论模式：读取 MOC 和相关 atoms

```bash
# 读取完整 idea 体系
obsidian vault="Research" read file="ideas/_map"

# 读取特定 atom
obsidian vault="Research" read file="ideas/h-proprio-beats-visual"

# 列出所有活跃的未解决问题
obsidian vault="Research" search query="#type/question #status/active"
```

---

## task-<name>.md 模板（LabPrompt 写入）

```markdown
---
type: task
status: pending   # pending | active | done
created: 2026-04-20
related: []       # 关联的 ideas atoms，如 ["[[h-xxx]]", "[[d-yyy]]"]
---

<!-- 每节对应一个可交给 Lab 执行的子任务 brief，风格参见 LabPrompt 的 <prompt-style> -->
```

> `tasks/` 是人的导航层，agent 不自动读取此文件夹。LabPrompt 写入，用户自主取用后开 Lab 执行。

---

## _context.md 模板

```markdown
# 研究语境：{项目名}

## 核心问题
<!-- 1-2 句话：这个研究在解决什么问题 -->

## 当前方向
<!-- 当前最重要的研究假设或实验方向 -->

## 活跃假设
- [[h-xxx]]：一句话描述

## 未解决问题
- [[q-xxx]]：一句话描述

## 最近决策
- [[d-xxx]]：一句话描述
```

## _progress.md 模板

每次 session 结束时由 lab-handoff 覆写，目标是让下一个 session 直接续接而无需重新调研。

```markdown
# 工程续接：{项目名}

## 当前目标
<!-- 正在做什么，1-2 句话 -->

## 当前进度
<!-- 具体到文件/函数级别：已完成哪些步骤 -->

## 未完成
<!-- 按优先级，具体且可操作 -->
- [ ] 最高优先级的下一步
- [ ] 次优先级

## 关键上下文
<!-- 续接时必须知道的：设计决策、踩过的坑、依赖关系 -->

## 相关文件
<!-- 涉及的关键文件路径 -->
- `/abs/path/to/file.py`：一句话描述作用

## 续接指引
<!-- 下一步从哪里开始，注意事项 -->

## 阻塞
<!-- 如有已知阻塞 -->
```

## _progress-history.md 模板（changelog 风格）

```markdown
# 工程历史：{项目名}

<!-- 每次 session 结束后追加一条，保持简洁 -->

## YYYY-MM-DD
- 完成：xxx, yyy
- 决策：zzz
- 遗留：aaa
```

---

## 使用原则

- **轻量读取**：正常对话只读 `_context.md` + `_progress.md`，不全量读 vault
- **按需深入**：只有在 idea 讨论模式或用户明确要求时，才读 `ideas/` 下的文件
- **追加优先**：用 `append` 而非覆盖，保留历史
- **atom 粒度**：每个 h/q/f/d 一个文件，便于 backlinks 和 tag 搜索
- **状态驱动**：通过 `property:set` 更新 status，而不是删除旧文件
