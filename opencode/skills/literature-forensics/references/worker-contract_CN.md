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
  max_new_papers: <非负整数>
  max_primary_reads: <非负整数>

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

- `fast`：搜索和 provider recommendations；读取候选标题、metadata 和摘要；禁止打开正文和遍历引用图。
- `normal`：允许补搜、选择性原文页核验，并从初始 seeds 出发最多扩展一跳引用。
- `deep`：不做广泛发现，只深入分析任务明确指定的核心论文。

`max_new_papers/max_primary_reads` 默认分别为：`fast: 10/0`、`normal: 8/5`、`deep: 0/3`。一次任务不得自行升级 profile。连续两次搜索没有新增高相关候选即结束 discovery。

## 返回

返回研究内容，而不是过程 telemetry：

1. 对 lane 问题的直接回答；
2. 三条影响最大的发现及论文名称；
3. 最强反证或不确定性；
4. lead 应核验的原文页或图；
5. 尚未解决的科学问题（如有）。

不要突出 task ID、artifact 路径、API 故障、query 日志或预算记账。必要的恢复信息写入分配的隐藏审计文件。
