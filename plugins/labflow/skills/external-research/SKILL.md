---
name: external-research
description: 外部资料调研技能。用于官方文档、第三方 API、上游源码、版本差异、论文、技术报告、标准、GitHub issue/PR 和迁移说明。优先使用 Context7 查官方文档/API，使用 gh CLI 查 GitHub release/source/issue/PR，必要时委派 lab-research background subagent。不要用于本地代码库架构或符号调研。
---

# External Research

本 skill 只处理**项目外部资料**。目标是把会影响实现的外部事实查清楚，并标注证据来源与版本不确定性。

本地代码库结构、符号、调用链使用 `codebase-research`。

## 证据优先级

按以下顺序取证：

1. 官方文档、API reference、迁移说明。
2. 版本化上游源码：tag、release、commit。
3. 论文、技术报告、标准。
4. maintainer 的 issue / PR / discussion。
5. blog、教程、示例代码；仅在以上来源不足时使用。

涉及 OpenAI / Codex 产品时，优先官方 OpenAI 文档。

## 工具选择

- **Context7**：如果当前 session 暴露 Context7 MCP/tool，官方文档、API reference、版本化库用法优先用它；它通常比泛 web 搜索更适合查“某库当前官方怎么写”。
- **`gh` CLI**：GitHub release、tag、issue、PR、discussion、上游源码片段，优先用 `gh`；需要精确源码时结合 `gh repo clone`/`gh api`/`gh pr view`/`gh issue view`。
- **web search / browser**：当 Context7 不覆盖、官方站点不在 GitHub、或需要横向查资料时使用；仍以官方来源为准。
- **pdf-reader**：论文、技术报告、PDF spec、远程 PDF 或需要抽图/分页定位时使用。
- **普通 shell 工具**：已下载的源码/文档可用 `rg`、`sed`、`git tag`、`git show` 等确认版本化事实。

## 推荐流程

### 1. 固定问题

先把外部问题写成可查证句子：

- 某 API 的签名、默认值、边界条件是什么？
- 某版本是否支持某能力？
- 官方推荐的迁移路径是什么？
- 论文中某公式/实验设置的原始定义是什么？

### 2. 决定主 agent 自查还是委派

主 agent 自己调研：

- 问题单一，答案大概率来自一个官方页面或一个 API reference。
- 当前实现马上依赖该答案，需要边查边改。
- 只需确认一个签名、默认值、配置项或迁移说明。

委派 `lab-research`：

- 有多个独立外部问题，可并行预取。
- 需要同时查官方文档、上游源码、GitHub issue/PR、paper。
- 需要深挖版本差异、历史行为、maintainer 讨论。
- 主 agent 正在实现或读本地代码，外部调研会挤占上下文。

### 3. 并行预取

多个独立外部问题可以拆给 `lab-research`：

- 一个 agent 查官方文档。
- 一个 agent 查上游源码或 GitHub issue。
- 一个 agent 查 paper / benchmark。

主 agent 等结果回来后，只保留影响当前实现的事实。

### 4. 版本化确认

凡会影响代码行为的结论，都尽量带上：

- 文档 URL 或仓库路径。
- 版本号、tag、commit 或发布日期。
- API 名称、参数名、默认值。
- 已知行为变化或不确定性。

## 输出格式

输出应包含：

- 结论：可直接指导实现的外部事实。
- 来源：URL / repo path / paper 信息，尽量带版本。
- 约束：默认值、边界条件、兼容性、已知坑。
- 实现影响：本项目应该如何使用或规避。
- 不确定性：证据缺口，不要伪装成确定结论。

## 反模式

- 用博客替代官方文档。
- 不标版本就讨论 API 行为。
- 把本地代码问题交给外部调研。
- 大段搬运资料，而不是提炼会影响实现的事实。
