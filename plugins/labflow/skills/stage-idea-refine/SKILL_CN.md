---
name: stage-idea-refine
description: 进入研究想法精细化阶段，用于规划或实现前的非线性研发讨论。
---

<Description>

当用户已经形成初步研究想法，但在规划或实现前仍需要澄清意图、可行性、技术路线、关键假设或方法选择时，进入 idea-refine stage。

这个阶段服务科研 R&D 的非线性讨论：目标不是立刻写 PRD 或实现，而是把模糊想法逐渐讨论成一个足够精炼、可进入下一阶段的研究方案。

## 边界

- 主要讨论研究想法、技术路线、方法选择、可行性风险、反例与证据需求。
- 工程细节可以讨论，但只作为研究可行性的支撑，不直接进入实现。
- 不替代 Codex native plan / implement；当方案已清晰，应退出 stage。
- 如果 stage 是因讨论文件名、hook、命令本身而误触，agent 应主动说明并用独立 `$labflow:stage-control cancel` 退出。

</Description>

<ExitReadiness>

`exit_readiness` 是显示在 HUD 与 hook 上下文里的离散状态：

- `vague`：连用户自己到底想做什么、需要什么都还不太确定。
- `not_ready`：有大致想法和较清晰目标，但技术路线、方案手段、潜在矛盾、可行性或合理性仍需讨论。
- `candidate`：已有较具体的候选方案，但部分关键细节尚待确定。
- `ready_to_pass`：精炼方案已形成，准备 pass 并退出 stage。

它不是线性进度条。科研讨论可能从 `candidate` 退回 `not_ready`，甚至因发现更深问题退回 `vague`。

`idea_state` 是自由文本，用来描述“当前这个研究想法被讨论成了什么样”。它比 `exit_readiness` 更有科研语义，也更适合给用户和 agent 回顾。

</ExitReadiness>

<Workflow>

agent 在讨论中自行识别状态变化，但不要把状态维护变成每轮仪式。

当出现以下明显变化时，应更新 stage state：

- 研究问题或目标发生改变。
- 关键假设被推翻或新增。
- 从模糊问题形成候选路线。
- 候选路线被反例打回。
- 方案已经足够精炼，准备退出。

使用脚本更新：

```bash
python3 scripts/update_idea_state.py \
  --state-path <hook 注入的 state file> \
  --exit-readiness candidate \
  --idea-state "当前研究想法状态的简短自由文本" \
  --note "本次为何更新"
```

`scripts/...` 路径按当前 skill 目录解析，不按 shell 当前工作目录解析；这是 Codex skill bundled resources 的官方约定。

`UserPromptSubmit` hook 会持续注入当前 `exit_readiness` / `idea_state`，提醒 agent 仍处在该 stage。hook 不负责理解科研语义，语义判断由 agent 完成。

</Workflow>

<Completion>

当 `exit_readiness=ready_to_pass` 时，agent 优先提醒用户发送 `$labflow:stage-control pass`。只有在用户明确要求 agent 代为退出 stage 时，才由 agent 自己输出独立 `$labflow:stage-control pass` 行。

真正 pass 退出后，agent 再按需写一份极短的 idea-refine brief，作为用户回顾材料，而不是执行 contract：

```bash
cat <<'EOF' | python3 scripts/write_refined_brief.py --state-path <passed state file>
# Idea Refine Brief

- 研究问题：
- 精炼方案：
- 关键假设：
- 暂缓/排除：
- 风险与证据：
- 下一步：
EOF
```

brief 存在 `.codex/labflow-stage/sessions/` 附近，只给用户回顾或复制到新会话使用，不会自动注入后续 stage。

</Completion>

<Abilities>

只在能服务当前 idea-refine 讨论时调用 ability。ability 是可选辅助，不是必须凑齐的流水线。

- `research-brainstorm`：当 idea 需要第一性原理手撕、候选方法生成、关键假设、反例、失败模式和最小验证实验时使用。
- `deep-research`：当可行性问题、技术路线、论文/API/代码事实或跨证据源结论会影响 idea 精炼时使用。

</Abilities>
