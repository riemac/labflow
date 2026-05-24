---
name: research-brainstorm
description: 面向科研 idea、算法路线、表示选择、实验设计、机器人/CV/ML 方法或科学假设的第一性原理头脑风暴；生成并批判候选方法，显式写出假设、反例、失败模式与最小验证实验。
---

<Description>

`research-brainstorm` 是一个 **ability skill**，不是 stage。

它适合在用户有一个科研想法、技术路线或方法选择，但还没到规划/实现阶段时使用。目标不是“列几个点子”，而是从第一性原理把 idea 拆开：它为什么可能成立、需要哪些隐含条件、哪里可能失败、怎样用最小实验快速验证。

它可以在 `stage-idea-refine`、`stage-goal-clarify` 或普通 Codex 对话中使用。它与 `codebase-research`、`external-research`、`deep-research` 都是相互独立的能力，不表示固定的先后流程。

</Description>

<CoreContract>

- 把用户当科研伙伴，而不是把用户需求包装成一个固定方案。
- 先看机制：几何、动力学、统计分布、表示、学习信号、优化压力、数据生成、仿真约束。
- 生成和批判同时进行：每个严肃候选 idea 都要有假设、反例、失败模式、最小验证。
- 允许轻量调研：如果某个事实可从本地代码、项目文档、官方资料或论文中快速核验，且会影响判断，可以查；但不要默认变成大综述。
- 保持轻量：默认输出方法卡片，不写长报告，不自动转入 plan / implement。

</CoreContract>

<Workflow>

## 1. 定框

先把问题压成一句话：

- 研究对象是什么？
- 想提升/验证的能力是什么？
- 评价指标是什么？
- 哪些变量可控，哪些是硬约束？
- 哪些事实已知，哪些只是直觉？

如果用户偏好会显著改变搜索空间，问一个聚焦问题；否则明确假设后继续。

## 2. 手撕 idea

围绕“这个 idea 要成立，世界必须长什么样？”来拆：

- 几何/拓扑/坐标系假设；
- 动力学/物理假设；
- 数据分布/仿真随机化假设；
- 网络表示/归纳偏置假设；
- 优化目标/奖励信号假设；
- 工程可落地假设。

主动提出至少一个反例或退化情形。

## 3. 生成候选方法

按问题选择相关轴，不必全覆盖：

- 表示与 tokenization；
- 模型结构与归纳偏置；
- loss / reward / learning signal；
- 数据生成、课程学习、domain randomization；
- simulator、morphology、physics；
- validator、ablation、metric；
- 与当前代码库/实验管线的集成成本。

## 4. 输出方法卡片

默认使用方法卡片：

```text
### <方法名>
- 核心想法：
- 为什么可能有效：
- 关键假设：
- 失败模式 / 反例：
- 最小验证实验：
- 成本 / 风险 / 新颖性：
- 与当前项目的契合点：
```

## 5. 收敛

把候选方案粗分为：

- `safe`：保守但稳；
- `promising`：值得优先试；
- `risky`：可能有高收益，但假设较重；
- `do-not-do`：看起来诱人但大概率浪费时间。

最后给 1-3 个下一步 probe，而不是直接写实现计划。

</Workflow>

<AntiPatterns>

- 不要强行形成 `brainstorm -> deep-research -> scaffold` 这类固定流水线。
- 不要把 brainstorm 写成 PRD、SPEC 或任务计划，除非用户明确要求离开 idea 阶段。
- 不要用泛泛建议糊弄，例如“可以试试 Transformer/GNN”，除非解释机制和最小验证。
- 不要把软件架构洁癖放在科研有效性之前。
- 不要假装确定；不确定性往往正是本 skill 的核心产出。

</AntiPatterns>
