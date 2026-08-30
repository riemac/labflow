---
name: autopilot
description: "仅当用户明确要求 autopilot、auto、autoresearch、无人值守、过夜或长程自主迭代时使用。先形成一次高层执行契约，再自主调研、实现、运行有界实验、分析证据、维护约定产物并持续迭代，直到成功、用户打断、预算耗尽或硬阻塞。仅用于 OpenCode；background subagent 和 PTY 退出通知负责事件驱动续航，用户手动开启的 Goal 是可选外部机制。"
---

# Autopilot

Autopilot 是经用户明确授权的 OpenCode 长程执行协议，不是新的 primary agent，不替代领域 skill，也不允许 agent 静默扩大权限。

## 启动与契约

只有用户明确表达“开始 auto 吧”“启动 autopilot”或同等执行意图后才进入 Autopilot。若对话中已经有 decision-complete 的 Plan 交接，应直接复用；若仍缺少会改变安全或科研语义的边界，在启动前用一个聚合问题确认。真正启动后直到结束或用户打断都不得调用 `question`。

契约必须确定一个主 profile（Research、Coding 或 Paper）、高层目标、成功证据、主题产物根、仓库/稿件工作区、由用户选定的 Git/worktree 策略、读写范围、高影响变更授权、资源与墙钟预算、提交策略、禁止的外部副作用和停止条件。用户没有指定时，墙钟默认 10 小时；不要为 Git 策略设置全局默认。

在 `labflow-plan` 中只形成只读计划和契约；切到 Build 并收到明确启动指令后才创建文件和执行。

## 自有产物

在用户批准的主题目录下只创建：

```text
.autopilot/
├── contract.md
└── autopilot.md
```

`contract.md` 冻结目标、边界、profile、预算和停止规则，agent 不得自行扩权。`autopilot.md` 动态维护当前状态、候选组合、仍在运行的 PTY/background subagent、关键证据与决策、下一波和最终交接。异步任务完成并被整合后，立即从 active 区移除，不复制 `pty_list` 或 child-session 的历史。

实验档案、学习诊断、论文、图表、代码、决策树、record、README、AGENTS 和 Obsidian 笔记继续遵循原有领域组织；Autopilot 可以维护并链接它们，但不在 `.autopilot/` 重复造一套。

## 自主循环

使用自适应循环：Orient → 形成机制不同的候选组合 → 选择最高信息增益动作 → Execute → Verify → Retain/Revert → Record → Reassess。不要固定迭代数，也不要因为连续几次失败就停止；先细化机制，再切换机制路线，再检索聚焦外部证据，只有没有可辩护的下一步时才形成失败边界报告。

## 最大有效并行

并行的目标是降低路线偏见和缩短证据时间，而不是填满硬件。启动运行型 probe/实验前，预告预期 GPU、显存、CPU、内存、磁盘、时长和输出；检查实时资源，未知峰值时先启动一个代表性 canary，在可靠 startup 信号或小规模完成结果后再分配同波剩余 PTY。会污染 wall-clock、吞吐、显存或随机性比较的任务必须串行。每条并行 lane 必须有不同问题、隔离写入/输出、配置身份和明确返回，主 agent 保留整合判断与所有长进程所有权。

## 事件驱动续航

短任务使用普通命令；独立读重证据使用 background subagent；长时、交互或正式任务使用 PTY。PTY 必须设置准确 workdir、描述性标题、`notifyOnExit: true` 和适用的安全超时。禁止 sleep/poll；只有资源分配或故障诊断需要实时证据时才做一次聚焦读取。

没有 Goal 时，background subagent 或 PTY 完成通知可以重新唤醒 agent；没有任何异步事件时，response 结束后 OpenCode 不会凭提示词自行醒来。Autopilot 不创建、暂停、恢复或完成 Goal。用户手动 `/goal` 可为纯代码/写作提供跨回合续航；background child 可由 Goal 门控等待，但 PTY 不是 child session，不应让 active Goal 和 active PTY 同时争夺下一轮驱动权。

## Git 与副作用

保护无关 dirty changes，只暂存本次工作。可以创建恢复锚点和有意义的 checkpoint commit，失败或低价值候选记录证据后安全丢弃。Autopilot 运行期间不得 bump、做 release closure、打 release tag、push、发布、部署、发送外部消息、购买资源、轮换凭据或修改生产，除非冻结契约逐项明确授权。不得用破坏性 Git 操作处理非本次运行创建的工作。

## Profile

每次只读一个主 profile：`references/research.md`、`references/coding.md` 或 `references/paper.md`。它们可以调用现有能力，但不会叠加成第二个 profile。

## 停止与交接

在成功证据满足、用户打断、10 小时或其他预算耗尽、安全边界触发、外部硬阻塞，或系统换路后仍无可辩护动作时停止。停止前处理活跃 PTY/子任务、保留有效产物、运行最强可承担终检、更新主题文档，并在 `autopilot.md` 写明结果、关键证据、保留 commits、失败路线、限制、风险和精确复现/恢复方法。不得把可行性证据冒充正式科研、工程或投稿验收。
