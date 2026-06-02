---
name: codebase-research
description: 本地代码库调研技能。用于架构追踪、符号定位、调用链梳理、类似实现查找、配置注册路径分析、跨文件数据流理解。使用本地语义检索、shell 搜索和关键文件精读；不要用于外部文档、论文或第三方 API 调研。
---

# Codebase Research

只用于**本地代码库调研**。外部文档、上游源码、release、GitHub issue/PR、论文、第三方 API 交给 `external-research`。

## 默认闭环

互不依赖的分支尽量最大并行化。

1. **语义检索**：把当前可用的本地语义检索 / code RAG 当作薄入口。一次查一个概念。始终限定到能辩护的最窄 repo、子项目或模块路径；证据变清楚后继续下钻。查询风格按具体工具自己的 skill/docs 来。
2. **Shell 缩小范围**：`tree` 看结构，`fd` 找文件，`rg` 找符号、配置键和字符串。必须加深度限制，并排除缓存、依赖、生成文件、日志、输出和数据目录。
3. **Read 精读**：读入口、定义、注册点、上下游各一层、类似实现、相关测试/示例。已知关键路径时直接读，不要强行先语义检索。

示例：

```bash
tree target_dir -L 3 -a -I '.git|__pycache__|.venv|node_modules|dist|build|logs|outputs|.cocoindex_code'
fd 'reward|manager|cfg' target_dir
rg -n "RewardManager|RewTerm|RewardsCfg" target_dir
```

## Subagent 委派

委派和默认闭环分开。只有多个独立分支会吃掉主上下文时才用。

- 每个 subagent 只给一个窄路径和一个具体问题。
- 要求返回路径、行号、不确定性，以及主 agent 必须精读的决定性文件。
- 不要把 subagent 输出原样当最终答案。
- 主 agent 必须亲自读决定性文件后再下实现判断。

## 输出

保持服务决策：

- 结论：本地代码实际如何工作。
- 证据：路径、行号、符号、配置键或调用链。
- 可复用模板：最接近的已有实现。
- 实现影响：下一步可能改哪些文件、接口或配置。
- 不确定性：哪些没读，为什么不阻塞当前决策。

## 避免

- 绑定某一个语义搜索 provider。
- 能缩小路径却做 workspace-wide 查询。
- 把检索结果或 subagent 摘要当证据。
- 不加深度/排除规则就输出巨大目录树。
- 写成泛泛架构介绍，而不是回答当前任务。
