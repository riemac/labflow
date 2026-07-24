# 文献 Worker Assignment 契约

每次新建或续接 `literature-worker` 时使用。Coordinator 应显式填写所有字段；缺少 profile 时的推断只是 worker 的恢复行为。

```yaml
research_root: <research 绝对路径>
brief: <research_root>/.research/brief.md
lane: <稳定 lane 名称>
question: <一个边界明确的科学问题>
decision_connection: <该 lane 为什么影响主决策>

profile: fast | normal | deep
language: <research 输出语言>
limits:
  max_full_papers: <非负整数>

scope:
  include: <纳入的 setting、机制和工作类型>
  exclude: <明确排除项>
  allowed_local_sources: <路径或 none>
  seed_identifiers: <identifiers 或 none>

write_targets:
  lane_audit: <research_root>/.research/audit/lanes/<lane>.md
  paper_audit_directory: <research_root>/.research/audit/papers/
```

## Profiles

- `fast`：搜索和 provider recommendations；读取候选标题、metadata、摘要和 targeted key pages；禁止完整 PDF 阅读和遍历引用图。
- `normal`：允许补搜、选择性原文页核验、完整阅读最强候选 PDF，并从初始 seeds 出发最多扩展一跳引用。
- `deep`：不做广泛发现，只完整阅读任务明确指定的核心论文 PDF。

`max_full_papers` 默认值为 `fast: 0`、`normal: 3`、`deep: 5`。它只统计本次 assignment 中首次达到 `review.worker: full` 的唯一论文：必须下载并验证 PDF、完整阅读主体，并核对 method、experiments/results、limitations/discussion 和与 lane 相关的全部 appendix。仅下载或打开 PDF 不算。标题、metadata、摘要、citation edge 和 targeted page check 都只是未计数候选证据，绝不能纳入“已调研、已阅读或已审阅论文”的数量。一次 assignment 不得自行升级 profile；同一 lane 和证据链应续接同一 task，coordinator 可以另发显式 assignment 切换 profile，包括从候选发现转入 deep 完整 PDF 阅读。连续两次搜索没有新增高相关候选即结束 discovery。

## 返回

返回研究内容，而不是过程 telemetry：

1. 对 lane 问题的直接回答；
2. 三条影响最大的发现及论文名称；
3. 最强反证或不确定性；
4. lead 应核验的原文页或图；
5. 尚未解决的科学问题（如有）。

不要突出 task ID、artifact 路径、API 故障、query 日志或预算记账。必要的恢复信息写入分配的隐藏审计文件。
