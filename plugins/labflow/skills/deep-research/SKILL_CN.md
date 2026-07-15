---
name: deep-research
description: 针对复杂科研或工程问题做深入调研，综合本地代码、项目文档、外部官方文档、上游源码、论文/PDF、API 或网页/GitHub 证据，并产出有证据链、结论边界和置信度的研究报告。
---

<Description>

`deep-research` 是一个 ability skill，不是 stage。它适合在 `stage-idea-refine`、`stage-goal-clarify` 或普通 Codex 对话中被调用，用来处理“短回答不够、必须查证和综合”的复杂问题。

典型问题：

- 某技术路线是否可行，边界条件是什么？
- 某框架是否支持某种系统设计？
- 本地代码、上游文档、论文之间的结论是否一致？
- 某科研方案是否有反例、隐藏假设或工程落地风险？

它的产物不是搜索结果堆砌，而是一份可审计、可用于决策的报告。

</Description>

<Workflow>

## 1. 问题定框

先把用户问题压成一句话，并拆成少量子问题：

- 需要回答什么决策？
- 哪些事实可从本地代码/文档发现？
- 哪些事实需要官方文档、上游源码、论文或 issue/PR？
- 哪些属于用户偏好或科研判断，不能靠检索自动决定？

如果某个偏好会显著改变报告结论，问一个聚焦问题；否则带着明确假设继续。

## 2. 收集证据

按证据强度选择工具：

- 本地代码：优先语义检索定位，再精读关键文件和行号。
- 外部库/API：优先 `find-docs` / ctx7；只有需要 GitHub 事实时再用 `gh`。
- 论文/PDF：用 `pdf-read`，保留页码、章节或提取路径。
- 高噪音分支：按照全局 **Background-First Prefetch** 协议委派 `lab-explore` / `lab-research` 吸收检索噪音；返回内容作为高信号预取，主 agent 必须核验驱动结论的关键证据。

## 3. 综合判断

报告必须区分：

- 已被证据支持的事实；
- 基于事实的推理；
- 面向用户任务的建议；
- 尚不确定或需要实验验证的部分。

尤其要主动写出边界条件、反例、失败模式和工程代价。

## 4. 产出报告

若用户要求保存，写到用户指定路径。若用户没有指定路径，默认先在对话中给出，不擅自落盘。

较重报告优先使用 `references/report-format.md` 的结构。

</Workflow>

<ReportStyle>

推荐报告结构：

```text
# <主题> 调研
## Executive Summary
## Direct Answers
## Architecture / System Overview
## What the Evidence Shows
## Implications / Recommended Route
## Key Repositories / Files / Sources
## Confidence Assessment
## Footnotes
```

写作风格：

- 结论先行；
- 表格回答直接问题；
- 机制解释要落到代码/文档/论文证据；
- 建议要服务用户当前科研任务；
- 置信度必须分层；
- 脚注用于保留可审计证据链。

</ReportStyle>

<AntiPatterns>

- 不把 deep research 写成泛泛综述。
- 不用“应该可以”掩盖 schema、shape、API、物理约束。
- 不把 subagent 输出原样当最终报告。
- 不用二手资料替代官方文档、源码或论文。

</AntiPatterns>
