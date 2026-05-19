---
name: external-research
description: 外部资料调研编排技能。用于第三方库/API、官方文档、上游源码、版本迁移、论文/PDF、GitHub release/issue/PR，以及高噪音/低信噪比的深度外部调研。默认优先 ctx7 CLI / find-docs；gh CLI 仅在需要 GitHub 证据时辅助；高噪音调研强烈委派 lab-research。不要用于本地代码库架构或符号调研。
---

# External Research

本 skill 只做轻量编排，不复制 ctx7 文档查询说明。

本地代码库结构、符号、调用链使用 `codebase-research`。OpenAI / Codex 产品问题使用 `openai-docs`。

## Default Route

- 库/API/官方文档/配置项/迁移说明：必须先使用 `find-docs` / ctx7 CLI。不要因为目标库托管在 GitHub，就先用 `gh` 查 repo 或源码。
- 只有问题本身需要 GitHub 证据时，才直接使用 `gh` CLI：release/tag 日期、issue/PR/discussion、上游源码实现、commit 差异、仓库元信息、npm/release 状态核对。
- 论文、技术报告、PDF spec、远程 PDF：使用 `pdf-read` / pdf-reader。
- ctx7 不覆盖、官方站点不在 GitHub、或需要横向资料时，再用 web search/browser。

判断顺序：先问“这是文档/API 用法问题吗？”如果是，ctx7 先行；再问“答案是否依赖 GitHub 事实或源码实现？”如果是，再补 `gh`。不要为了形式上的交叉验证而扩大工具面。

## Bootstrap

如果需要 ctx7 但本机没有 `ctx7` 命令，先运行 helper：

```bash
bash <plugin-root>/skills/external-research/scripts/ctx7_bootstrap.sh status --json
bash <plugin-root>/skills/external-research/scripts/ctx7_bootstrap.sh ensure --yes
```

`ensure` 只负责安装/配置 `ctx7`、`find-docs`、`context7-cli`；不要把它当查询接口。

## Delegate

遇到高噪音、低信噪比、需要多跳搜索的外部调研时，强烈委派 `lab-research`。核心目的不是“能力不足”，而是让 subagent 吸收检索噪音，避免主 agent 的上下文被长网页、issue 串、半相关结果和无效文档污染。

典型信号：

- 单次 ctx7 / web / gh 查询大概率不能直接回答。
- 搜索结果很多，但真正有效信息只占很小比例。
- 需要翻多个 issue、PR、discussion、release note 或长文档才能找到关键事实。
- 调研方向之间相对独立，可以并行拆给多个 subagent 预取。
- 主 agent 后续还要实现或设计，不应把大量检索噪音带进主上下文。

委派时优先轻量模型，例如 `gpt-5.4-mini`，除非任务本身需要深推理。

## Keep It Small

- 保留会影响实现的事实、来源 URL/repo path、版本号/发布日期和关键不确定性。
- 把大范围检索、反复试错和无效材料留在 subagent 上下文里。
- 不大段搬运资料。
- 不为了“完整调研”强行使用所有工具。
