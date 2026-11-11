---
name: stage-driven-research
description: >-
  用于引导构建阶段驱动科研笔记的元技能。用于为课题初始化全新的 Research/ Obsidian 知识库，或在已有知识库中脚手架化新的实验阶段。初始化完成后，日常 agent 的行为完全由生成的层级 AGENTS.md 驱动，不再反复调用本技能。
---

# 阶段驱动科研（Stage-Driven Research）

为课题一次性生成科研笔记脚手架的元技能。初始化完成后，`Research/` 目录内部的嵌套 `AGENTS.md` 规则体系将统领后续所有实验记录与科研语义追踪行为。

## 核心理念

### 阶段驱动演进（Stage-driven development）

科学研究——特别是在机器人学、机器人学习与 Sim2Real 领域——本质上是通过有界的实验战役（bounded experimental campaigns）向前推进，而非连续零散的代码提交。每次实验战役聚焦于特定的科学假设，通过可复现的受控实验积累证据，并最终以提炼出认知增量的复盘回顾（Retrospective）宣告收尾。

**阶段驱动开发（Stage-driven development）** 将这一科研节奏规范化：

1. **Stage 是有界的科研战役，而非日历周期**：Stage 始于具体科学假设的提出，终于凝练认知的 `STAGE-REVIEW.md`。多个 stage 在日历时间上可以重叠，但在逻辑和语义上保持独立。
2. **Run 是不可分割的原子事实源**：每一次实验——无论是成功验证、负结果消融还是诊断探针——均以 run card 形式落盘，记录完整的可复现元数据（代码 commit、启动命令、产物路径、dirty-worktree 标记等）。Run card 是自包含的客观事实源。
3. **MAP 刻画科研语义状态的演进 DAG**：具有里程碑意义的 run 在其 YAML 头标记 `node_id`，晋升为 Mermaid 有向无环图（`MAP.md`）中的节点。MAP 编码因果继承与消融关系——它是科研认知状态的拓扑图，而非单纯的时间线。
4. **晋升具有严格的选择性**：只有越过能力门、改变机制判断、促成主路线转向、或具有长期参考价值的关键负结果，才会被晋升为 MAP 节点。常规 checkpoint 续训和冒烟测试仅保留为普通 run。
5. **单向依赖流：runs → MAP**：Run card 永远不反向引用 node ID 或 MAP 链接。删除或重构图谱决不影响实验记录本身的客观语义。
6. **模板按阶段人机协商定制**：不同 stage 涉及不同的科研形态（强化学习、三维场景重建、Sim2Real 实机部署、资产生成等）。进入新阶段时，agent 与研究者基于基础母版，结合该阶段特定的指标、数据产物和评估门槛，协商定制专属的 run-card 模板。

### 科研笔记体系（The research notebook）

`Research/` 目录是一个兼容 Obsidian 的科研知识库，将个人思维演变与客观实验事实解耦：

- **个人笔记区**（`总体/`、`进展/` 等）：由研究者个人撰写与维护，agent 严格保持只读，仅作为理解背景的上下文。
- **阶段演进区**（`stages/`）：人机共读、共写的实验记录与语义图谱区，在此记录实验、追踪状态并沉淀阶段复盘。

在每个 stage 目录内部，实验记录（runs）与科研语义图谱（MAP）高度内聚、合二为一，不再设立彼此割裂的 `图谱/` 与 `实验记录/` 根目录。Run card 的 YAML 头兼具节点属性，实现实验事实源与图谱身份的统一。

## 生成的目录结构

```text
<workspace>/
├── .agents/skills/stage-research/
│   └── SKILL.md                         # 项目级极简技能存根
│
└── Research/
    ├── AGENTS.md                        # 根规则：排版语法、读写边界、Codex 专节
    └── stages/
        ├── AGENTS.md                    # 阶段规则：stage 结构、run-card 规范、MAP 规则
        └── <stage_name>/               # 后续由日常 agent 依阶段创建
            ├── README.md                # 阶段背景与核心问题说明
            ├── MAP.md                   # 阶段科研语义 DAG（Mermaid）与节点索引
            ├── template/
            │   └── run-card.md          # 针对该阶段定制的 run-card 模板（与用户协商共创）
            ├── runs/                    # 01-name.md, 02-name.md, …
            ├── supplementary/           # 短探针、跨 run 归因分析（可选）
            ├── plans/                   # 实验规划（可选）
            ├── assets/                  # 图表与凝练化证据（可选）
            ├── scripts/                 # 作图与分析脚本（可选）
            └── STAGE-REVIEW.md          # 阶段结题回顾与证据链提炼
```

## 初始化工作流（仅执行一次）

1. 在目标工程位置创建 `Research/` 与 `Research/stages/` 目录。
2. 将 [research-root-agents.md](./references/templates/research-root-agents.md) 复制到 `Research/AGENTS.md`，随后替换项目专属占位符（`{{PROJECT_NAME}}`、`{{CODE_REPO}}`）。
3. 将 [stages-agents.md](./references/templates/stages-agents.md) 复制到 `Research/stages/AGENTS.md`，随后替换占位符（`{{PROJECT_NAME}}`）。
4. 将 [project-skill-stub.md](./references/templates/project-skill-stub.md) 复制到工程根目录下的 `.agents/skills/stage-research/SKILL.md`。
5. 向用户呈现生成的目录骨架以供核对。**初始化即告完成，本元技能不再被调用。** 后续的新阶段创建、实验记录与图谱演进，完全由日常 agent 依照项目本地各级 `AGENTS.md` 原生完成。

## 参考模板列表

| 模板文件 | 作用说明 | 目标生成路径 |
| --- | --- | --- |
| [research-root-agents.md](./references/templates/research-root-agents.md) | 顶层知识库规约、格式规范与 Codex 约束 | `Research/AGENTS.md` |
| [stages-agents.md](./references/templates/stages-agents.md) | 阶段演进规约、簇状 MAP 拓扑与入图准则 | `Research/stages/AGENTS.md` |
| [project-skill-stub.md](./references/templates/project-skill-stub.md) | 工程根目录极简技能存根 | `.agents/skills/stage-research/SKILL.md` |
