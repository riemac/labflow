---
name: stage-design-scaffold
description: 进入设计脚手架阶段。用于成熟想法进入实现前，把设计语义沉淀到代码或文档中的分布式 prompt：TODO、docstring、字段说明、接口壳、模块说明或设计锚点；默认不做完整实现。
---

<Description>

当 idea 已经相对成熟，但还不适合直接实现，而是需要先写入项目中的多个落点时，进入 `stage-design-scaffold`。

这个 stage 的核心不是继续 brainstorm，也不是写完整代码，而是把设计语义放到最贴近未来实现的位置：字段说明、TODO 伪算法、接口壳、模块注释、markdown design note 等。

</Description>

<Contract>

- 保持 design-scaffolding mode，直到 stage passed 或 cancelled。
- 先读本地代码/文档，能发现的落点不要问用户。
- 将已达成合意的设计意图写成分布式 prompt。
- 保留科研语义：假设、约束、公式、示例、边界条件、验收信号。
- 默认不写完整实现，除非用户明确退出 stage 或要求实现。
- 允许非线性推进：同一 stage 可以完成一个文件后转向另一个文件，也可以用户 review 后回到旧落点修改。

</Contract>

<StateSemantics>

`problem_statement` 是所有 stage 共享的问题锚点：当前这个 scaffold 要保留的问题或目标是什么。`problem_clarity` 表达这个锚点有多清楚：

- `unknown`：agent 还不能可靠复述问题。
- `fuzzy`：大方向存在，但对象、边界、动机、成功信号或约束还不稳。
- `framed`：问题已经能被清楚复述，用户大体认可。
- `stable`：问题表述足够稳定，可以作为当前 stage 的锚点；不是问题已经解决，也不是永久锁死。

Design scaffold 通常应该沉淀 `framed` 或 `stable` 的问题锚点和设计意图。若问题仍是 `unknown` 或 `fuzzy`，应先澄清问题，不要机械写大量分布式 prompt。

`scaffold_readiness` 是 HUD / hook 上下文显示的离散状态：

- `mapping`：正在定位设计目标、落点和开放问题。
- `scaffolding`：正在写分布式 prompt。
- `reviewing`：等待或吸收用户对脚手架内容的审阅。
- `ready_to_pass`：脚手架已足够，可以退出 stage。

同时维护一张轻量地图：

- `design_goal`：这次要沉淀的设计目标。
- `target_surfaces`：可能写入的文件、模块、类、配置或文档。
- `current_surface`：当前正在讨论或编辑的落点。
- `completed_surfaces`：已完成脚手架的落点摘要。
- `open_questions`：仍需用户判断的设计问题。

这些状态不是每轮仪式，只在设计目标、落点、完成项或开放问题明显变化时更新。

```bash
python3 scripts/update_scaffold_state.py \
  --state-path <hook 注入的 state file> \
  --problem-statement "当前 scaffold 要保留的问题或目标" \
  --problem-clarity stable \
  --scaffold-readiness scaffolding \
  --design-goal "当前设计目标" \
  --target-surfaces "module.py: 配置字段; docs/foo.md: 设计说明" \
  --current-surface "module.py: 配置字段" \
  --open-questions "仍需用户判断的问题" \
  --note "本次为何更新"
```

标记某个落点完成：

```bash
python3 scripts/update_scaffold_state.py \
  --state-path <hook 注入的 state file> \
  --scaffold-readiness reviewing \
  --add-completed-surface "module.py: 配置字段脚手架已写好" \
  --note "等待用户审阅"
```

`scripts/...` 路径按当前 skill 目录解析，不按 shell 当前工作目录解析。

</StateSemantics>

<ScaffoldingStyle>

好的 design scaffold 应该像代码库的一部分，而不是聊天记录。

优先使用：

- 声明式配置字段下的 `r"""..."""` 长说明。
- class / function docstring 表达语义契约。
- 包含输入、输出、约束、验收的 TODO 块。
- 当命名和数据流稳定时，写薄接口壳。
- 跨文件设计用 markdown note。

避免：

- 不约束实现的泛泛注释。
- 脱离目标代码的大段集中式 prompt。
- 因为打开了文件就顺手完成实现逻辑。

</ScaffoldingStyle>

<Completion>

当分布式 prompt 足以让未来实现者不必重新猜设计意图时，可以退出 stage。

当 `scaffold_readiness=ready_to_pass` 时，agent 优先提醒用户发送 `$labflow:stage-control pass`。只有用户明确要求 agent 代为退出 stage 时，才由 agent 输出独立 `$labflow:stage-control pass` 行。

</Completion>

<Abilities>

仅在服务当前 scaffold 时调用其他能力：

- `codebase-research`：定位落点和类似实现。
- `deep-research` / `external-research`：核验会影响设计脚手架的外部或跨证据事实。
- `annotation`：设计内容清楚后，润色注释和 docstring。

</Abilities>
