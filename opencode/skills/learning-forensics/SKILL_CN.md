---
name: learning-forensics
description: 当监督、无监督、自监督、生成、强化学习或机器人学习系统出现平台、发散、塌缩、过拟合、未超过基线、行为异常或需要证据驱动调优时使用。构造具体问题的学习因果链，组织不受主代理假设污染的并行 learning-worker（学习取证子代理）调查，定位最早断点，并设计有界判别探针。适合复杂学习归因；普通画曲线、已知简单报错和大规模超参搜索使用更直接的工具。
---

# Learning Forensics（学习系统取证）

<mission>

> [!abstract] 核心目标
> 面对失败的学习行为，定位学习因果链中最早断裂的环节，再用最小判别探针决定解决路线。

默认模板为：

$$\large
\text{数据 / 任务}\rightarrow\text{信号 / 目标}\rightarrow\text{可观测输入 / 经验}\rightarrow\text{表征}\rightarrow\text{函数类}\rightarrow\text{目标 / 估计器}\rightarrow\text{梯度}\rightarrow\text{更新}\rightarrow\text{行为 / 预测}\rightarrow\text{评估}
$$

这套模板可以随监督、无监督、自监督、生成、强化学习、机器人等具体问题增删或重命名节点，调查始终优先定位最早缺乏证据支持的转换关系。

</mission>

<coordinator_contract>

主代理作为研究负责人和最终证据所有者，主动阅读项目合同、源码、训练产物与进程状态，构造具体因果图，冻结无假设案卷，选择真正独立的调查视角，核验驱动结论的关键事实，解决子代理冲突，并独占人类可见报告与最终实验决定。

子代理用于提高覆盖率和提供独立因果解释；主代理继续承担推理、证据裁决和最终诊断。

</coordinator_contract>

<causal_model>

## 因果图写具体合同，不写偏好假设

每个节点记录本项目中的具体对象、权威公式或接口、源码路径、输入输出、单位、形状、掩码、分母、样本总体、预算、不变量、现有证据与缺失信息。盲审案卷聚焦算法合同和已观测事实；原因判断进入子代理调查与后续综合。

强化学习、在线学习、主动学习、自训练和模型生成数据采用显式反馈图，记录行为如何改变下一轮经验分布、估计器和更新；on/off-policy、探索、bootstrap、target network 和 replay 时效都属于因果边。

## 所有视角共享第一性原理横轴

- 可辨识性与可观测性；
- 信息是否足以跨过表示或估计器；
- 对称性、不变性、等变性、gauge 与坐标约定；
- 采样支持集、统计测度、掩码、权重与评估总体；
- 量纲、尺度、条件数、归一化和数值范围；
- 偏差、方差、随机噪声、标签/奖励噪声与梯度信噪比；
- 因果干预、反事实、负对照和反例；
- 可微性、离散切换、估计器假设与近似误差。

大 loss、大梯度或大更新不代表信息有效；训练标量下降也不代表目标总体行为被学会。

</causal_model>

<case_protocol>

## 建立或恢复本地调查目录

使用标准库 helper 初始化和校验目录：

```bash
python3 scripts/case.py init --path <case-root> --language zh-CN --title "<标题>" --question "<有界问题>"
python3 scripts/case.py validate --path <case-root> --json
```

在 skill 目录外调用时使用脚本绝对路径。helper 需要 Python 3.9 或更新版本，只管理结构，不诊断学习问题，也不执行实验。

## 冻结盲审案卷

```bash
python3 scripts/case.py new-case --path <case-root>
python3 scripts/case.py seal-case --path <case-root> --case case-0001.md
```

案卷保存症状、待支持的决定、因果图客观合同、权威设计源、原始观测、不变量、证据指针、安全约束与缺失事实；主代理偏好的原因、排序后的假设、调参建议和子代理结论进入封存案卷之外的调查层。

> [!important] Blind 边界
> `authoritative_design_sources` 与 `withheld_diagnosis_sources` 分开维护。盲审子代理读取项目说明、公式、配置、schema、源码和分布式设计提示，第一轮隔离既有调优猜测。所有首轮子代理接收同一案卷路径与 SHA-256；事实变化时新建下一编号案卷。

</case_protocol>

<parallel_investigation>

## 初次全面排查的八个候选视角

1. 数据、信号、目标、教师、奖励与经验分布；
2. 可观测性、可辨识性、问题机理与领域假设；
3. 学习/工程表征及信息保留；
4. 网络结构、路由、归纳偏置与函数类容量；
5. 目标函数、估计器、掩码、归约、基线与统计测度；
6. 梯度几何、优化器动力学、调度、裁剪与多任务更新；
7. 精度、累积、分布式、恢复、缓存、运行时与基础设施；
8. 评估有效性、公平比较、检查点选择与判别实验设计。

每个调查视角规定主要关注点，同时允许追踪必要的上下游证据。主代理删除不适用项、增加问题专用项并合并重复问题。面对真正陌生且信息不足的失败，第一轮最多可并行八个盲审子代理；后续只续接有信息增益的视角。

## 防止群体共振

每个子代理读取同一封存案卷，并获得自己的主要视角、因果范围、有界问题、决策联系、深度档位、调查范围、预算与独占写入目标。主代理偏好的解释保留在首轮委派之外。

OpenCode 使用 Task 工具的 `learning-worker`，设置 `background: true`。每个委派记录子代理所有权和案卷摘要，返回的 `task_id` 写入 `.learning/state/workers.json`。相同证据链续接原任务，完成通知代替轮询和重复调查。

盲审返回后按机制、证据和反证做冲突表，不按同意人数投票。相关问题优先续接原任务；`cross-examination`（交叉质询）阶段可以显式提供竞争证据。

</parallel_investigation>

<probe_and_tuning>

探针优先选择高预期信息增益、低计算成本、低时间、低代码侵入和低污染风险的方案。需要数值排序时，先把各项归一化为当前案例内的无量纲评分：

$$\large
S=\frac{\widehat I}{\epsilon+w_c\widehat C+w_t\widehat T+w_r\widehat R+w_x\widehat X}
$$

优先使用公式检查、固定批次审计、小样本过拟合、冻结模块读取器、oracle（真值）特征、干预/打乱、梯度方向一致性、匹配优化器对照和冻结总体评估。

子代理进入 `phase: probe` 前声明真假两种结果的预期、输入、冻结证据、隔离写入路径、600 秒上限、最多一个 GPU 进程和停止条件。子代理使用普通 shell 硬超时，持久脚本、结果和临时中间文件都写入 `.learning/probes/<probe-id>/`。项目源码变更以提案形式返回主代理；正式运行、检查点、缓存和正式训练预算继续由主代理拥有。

长时间或正式实验由主代理拥有。启动前询问用户，保存版本化科学配置和独立输出目录。OpenCode 有 PTY/后台会话工具时遵守全局规则；Codex 使用宿主原生后台能力。通用子代理继续承担证据工作，进程完成依靠后台工具的原生通知。

</probe_and_tuning>

<synthesis_and_reporting>

结论指出当前证据支持的最早断点、仍然竞争的一小组断点，或由于缺少关键量而不可辨识，并区分局部拟合能力、优化、总体学习、泛化、迁移和系统性能。

主代理写 `overview.md`、动态 `topics/*.md` 和可选 `assets/`，只为本案例真正重要的维度形成完整论文式报告。子代理写 `.learning/audit/lanes/` 与 `.learning/probes/` 授权文件；主代理拥有中央状态、交叉质询、决策树、过程记录和所有人类可见文件。

</synthesis_and_reporting>

<routing>

- 客观案卷格式：`references/case-schema.md`；
- 调查目录所有权：`references/dossier-layout.md`；
- 委派与返回格式：`references/assignment-schema.md`；
- 人类专题报告写法：`references/topic-report_CN.md`；
- 小探针边界：`references/probe-protocol.md`；
- 外部代码/文档/论文取证：`references/external-evidence.md`；
- 某个主要视角的专业纵深：`references/lenses/` 下对应文件。

</routing>

<common_drift>

> [!question] 常见偏航
> 通用超参数清单、偏好假设广播、语义重复的并行任务、以子代理投票代替证据、脱离基线和统计总体解释原始损失、用梯度大小代替信息质量、过早运行正式预算，都会降低定位最早断点的效率。

</common_drift>
