# Research AGENTS.md

本目录是 {{PROJECT_NAME}} 的科研 Obsidian vault，记录进展、研究想法、方案和人工判断。

依赖方向固定为 `Research -> {{CODE_REPO}}`：Research 可以引用代码仓库的代码、配置、commit、日志与运行接口，但代码仓库不应 import、解析或要求本 vault 存在。

## 结构

`总体/` 和 `进展/` 是用户个人科研笔记区，agent 只读，不主动改写。

`stages/` 是人机共读、共写的阶段性实验记录与科研语义图谱区。每个子目录代表一个有界的实验课题（stage），内含实验记录（`runs/`）、科研语义 DAG（`MAP.md`）、补充分析（`supplementary/`）及阶段复盘（`STAGE-REVIEW.md`）。用户显式授权时，agent 可以在这里创建或追加实验记录、维护图谱与模板。

## 格式

agent 与用户皆需遵守的编辑格式约定。

### 数学格式

行间数学公式：

```latex
$$\Large
<formula>
$$
```

行内数学符号使用 `$\large <symbol>$`，使渲染结果阅读友好。agent 平台自身的输出不使用 `\Large` 或 `\large`。

### 文本

- 完整的段落和句子直接一行书写，Obsidian / VSCode 会正确渲染换行。
- 利用 Obsidian 双链 `[[链接内容]]`、`[[目标|显示内容]]` 等特性。
- 避免中英文混杂滥用，以完整自然的中文描述为主，必要专业术语可用英文。
- 禁止过度防御性表述（如"不是…而是…"、"不得…"、"不能…"）。
- 措辞语气和用户接近。

### Obsidian 特性

适量使用 Obsidian Callout（`> [!abstract]`、`> [!question]` 等）对摘要和关键内容突出，主要正文保持正常文本。可适当使用：

- 链接：标题级与块级、外部链接、别名显示
- Transclusion：嵌入其他笔记或其一部分
- 脚注 `^` 和引用 `>`

## Git

Research Obsidian 笔记项目为独立 git 仓库，agent 可使用 git 相关操作。

## Codex 指南与行文约束

以下约束专门面向 Codex agent，Antigravity agent 可忽略本章节。

- 严格禁止防御性措辞。用 paper flavor 式自然流畅、完整凝练的文本撰写实验记录与图谱节点。
- 科研事实断言遵循证据层级：明确区分固定评估结果（hard evidence）、训练过程观察（soft evidence）和推测性解释（hypothesis）。
- 当实验记录或图谱节点的叙述质感需要提升时，可调用 `agy`（Antigravity CLI）或衔接 `antigravity-writing` 技能进行学术润色。
