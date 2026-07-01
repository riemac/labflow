---
name: codebase-research
description: "当 agent 需要在回答或编辑前检查本地仓库时使用：追架构、找符号、梳理调用链/数据流、找类似实现、检查配置注册路径、判断该读或该改哪些文件。使用并行 shell 探测、关键文件精读和 subagent 预取。不要用于外部文档、论文或第三方 API 调研。"
---

## 默认闭环

目标是快速找到当前任务真正相关的文件和代码路径。

积极最大并行化：先把任务拆成互不依赖的分支，然后并行启动 shell 探测和明显需要读的文件。不要等一个搜索结束后才发起其他独立搜索。

1. **Shell 缩小范围**：`tree` 看结构，`fdfind` 找文件（优先于常规 `find`），`rg` 找符号、配置键和字符串（优先于常规 `grep`）。必要时加深度限制，并排除缓存、依赖、生成文件、日志、输出和数据目录。
2. **Read 精读**：读入口、定义、注册点、上下游各一层、类似实现、相关测试/示例。已知关键路径时直接读，不要强行先做穷举搜索。

示例：

```bash
tree target_dir -L 3 -a -I '.git|__pycache__|.venv|node_modules|dist|build|logs|outputs'
fdfind 'reward|manager|cfg' target_dir
rg -n "RewardManager|RewTerm|RewardsCfg" target_dir
```

## Subagent 委派

委派和默认闭环分开，把它当预取用：只要陌生子系统、跨模块链路或多个候选实现可能吃掉主上下文，就尽早派窄范围 subagent；主 agent 同时继续本地搜索和精读，不要等阻塞后才派。

- 优先给窄范围；但问题本身跨模块时，可以让一个 subagent 覆盖多个相关模块。互不依赖的分支拆成多个 subagent 并行。
- 要求返回有用路径、行号、可能入口和剩余不确定性。
- 把 subagent 结果当作可信预取；只有下一步回答或编辑依赖精确代码细节时，再补读关键文件。

## 避免

- 能缩小路径却做 workspace-wide 搜索。
- 不加深度/排除规则就输出巨大目录树。
