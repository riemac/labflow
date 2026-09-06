---
name: codebase-research
description: "当 agent 需要在回答或编辑前检查本地仓库时使用：追架构、找符号、梳理调用链/数据流、找类似实现、检查配置注册路径、判断该读或该改哪些文件。使用路径受限的 shell 探测、关键文件精读，并在确实能保护主上下文时用 explore-worker 做有边界的预取。不要用于外部文档、论文或第三方 API 调研。"
---

## 默认闭环

目标是快速找到当前任务真正相关的文件和代码路径。

独立的 shell 探测和明显需要读的文件可以并行，以缩短同一项有边界的调查；不要为了追求并行度，把一条连贯代码路径拆成重复检索。

1. **Shell 缩小范围**：`tree` 看结构，`fdfind` 找文件（优先于常规 `find`），`rg` 找符号、配置键和字符串（优先于常规 `grep`）。必要时加深度限制，并排除缓存、依赖、生成文件、日志、输出和数据目录。
2. **Read 精读**：读入口、定义、注册点、上下游各一层、类似实现、相关测试/示例。已知关键路径时直接读，不要强行先做穷举搜索。

多文件搜索结果优先使用 `rg -n --heading`，避免重复长路径；下游工具需要每条结果自包含时，改用 `--no-heading` 或 `--json`。

示例：

```bash
tree target_dir -L 3 -a -I '.git|__pycache__|.venv|node_modules|dist|build|logs|outputs'
fdfind 'reward|manager|cfg' target_dir
rg -n --heading "RewardManager|RewTerm|RewardsCfg" target_dir
```

## Subagent 委派

委派时遵循全局探索档位和 **Background-First Prefetch** 协议。陌生子系统、跨模块链路、替代命名或多个候选实现可能吃掉主上下文时，使用 `explore-worker`；已知文件或少量目标直接读取。

- Assignment 中传递 `profile`、目标路径或排除范围、已知符号、代码问题和预期路径/行号；默认 `normal`。
- 一条调用链或一个子系统默认只用一个 worker；只有代码路径真正独立时才并行委派。
- 把 subagent 结果当作高信号预取；凡是直接驱动下一步回答或编辑的精确代码细节仍需核验。

## 避免

- 能缩小路径却做 workspace-wide 搜索。
- 不加深度/排除规则就输出巨大目录树。
