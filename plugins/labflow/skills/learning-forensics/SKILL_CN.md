---
name: learning-forensics
description: 当监督、无监督、自监督、生成、强化学习或机器人学习系统出现平台、发散、塌缩、过拟合、未超过基线、行为异常或需要证据驱动调优时使用。先判断 primary（主代理）直接诊断是否足够；正式启动后全面构造因果案例，组织不受主代理假设污染的并行 learning-worker（学习取证子代理）调查，再随证据动态收缩或重新扩展。普通画曲线、已知简单报错和大规模超参搜索使用更直接的工具。
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

<engagement_gate>

## 查看 Skill 不等于正式启动

加载或参考本 skill 时，先检查直接症状、项目合同、现有产物、错误行动的成本和最便宜的判别方式。若可能断点局部、事实容易直接读取、小脚本或有界 PTY 探针即可回答，且首次行动出错代价较低，则由主代理直接处理；此时仍可使用普通 read-heavy 检索与最大有效并行，但不创建 dossier，也不启动完整 worker round。

当最早断点可能跨越多个因果节点、观测互相冲突、候选解释导向代价显著不同的行动、系统不明原因低于基线，或设计者确认偏差会影响决定时，正式启动 Learning Forensics。主代理先说明启动理由，再创建或恢复一个 dossier，并执行下述全面首轮合同。

直接处理与正式启动采用同一套因果严谨性；区别只是盲审委派、持久化和审计基础设施的强度。

</engagement_gate>

<coordinator_contract>

主代理作为研究负责人和最终证据所有者，主动阅读项目合同、源码、训练产物与进程状态，先决定直接诊断是否足够。正式启动时完整构造案例因果图、冻结无假设案卷，并以最大有效并行启动所有实质相关且不重复的 blind causal lanes（盲审因果视角）。

全面首轮返回后，主代理按证据和信息增益收缩、暂停或重新扩展委派，核验驱动结论的关键事实，解决子代理冲突，并独占人类可见报告与最终实验决定。主代理默认亲自执行最小判别探针，并对相互独立的探针使用资源安全的最大有效并行。

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

## 正式启动后建立或恢复本地调查目录

使用标准库 helper 初始化和校验目录：

```bash
python3 scripts/case.py init --path <case-root> --language zh-CN --title "<标题>" --question "<有界问题>"
python3 scripts/case.py validate --path <case-root> --json
```

在 skill 目录外调用时使用脚本绝对路径。helper 需要 Python 3.9 或更新版本，只管理结构，不诊断学习问题，也不执行实验。

一个 dossier 表示一个持续调查身份。只要学习对象和需要支持的核心决定语义不变，新 checkpoint、指标、局部假设、探针和因果焦点的小幅漂移都复用同一 dossier。只有模型/任务/数据对象或核心决定发生显式重大改变，或用户明确要求分开调查时，才创建新 dossier。

## 冻结盲审案卷

```bash
python3 scripts/case.py new-case --path <case-root>
python3 scripts/case.py seal-case --path <case-root> --case case-0001.md
```

案卷保存症状、待支持的决定、因果图客观合同、权威设计源、原始观测、不变量、证据指针、安全约束与缺失事实；主代理偏好的原因、排序后的假设、调参建议和子代理结论进入封存案卷之外的调查层。

> [!important] Blind 边界
> `authoritative_design_sources` 与 `withheld_diagnosis_sources` 分开维护。盲审子代理读取项目说明、公式、配置、schema、源码和分布式设计提示，第一轮隔离既有调优猜测。所有首轮子代理接收同一案卷路径与 SHA-256。普通进展、worker 返回、新指标和假设收缩不需要新案卷；只有后续 blind round 确实需要更新后的重要事实时，才在同一 dossier 内创建并封存下一编号 case snapshot，永不修改旧快照。

</case_protocol>

<parallel_investigation>

## 正式启动后的全面首轮

1. 数据、信号、目标、教师、奖励与经验分布；
2. 可观测性、可辨识性、问题机理与领域假设；
3. 学习/工程表征及信息保留；
4. 网络结构、路由、归纳偏置与函数类容量；
5. 目标函数、估计器、掩码、归约、基线与统计测度；
6. 梯度几何、优化器动力学、调度、裁剪与多任务更新；
7. 精度、累积、分布式、恢复、缓存、运行时与基础设施；
8. 评估有效性、公平比较、检查点选择与判别实验设计。

每个调查视角规定主要关注点，同时允许追踪必要的上下游证据。正式启动后的第一轮先映射完整因果链，只删除可证明无关或语义重复的视角，增加问题专用项，并在运行时允许时并行启动其余所有独立 blind lanes。首轮默认 `normal`，只有天然跨多节点或高度模糊的问题使用 `deep`，总数继续以八个为上限。全面覆盖追求最大有效因果广度，不机械地为每个标签创建 worker，也不重复解析同一个问题。

共享事实包只构造一次：sealed case、evidence index、权威源码指针、run identity 和已经计算的客观数值。所有 worker 获得相同 case identity，只补充各自 lane 必需的来源；worker 运行时主代理继续非重复工作。

## 防止群体共振

每个子代理读取同一封存案卷，并获得调查阶段、自己的主要视角、因果范围、有界问题、决策联系、深度档位、共享事实包、调查范围、预算、独占写入目标，以及 exceptional worker probe（例外子代理探针）所需的理由。主代理偏好的解释保留在首轮委派之外。

Codex 优先使用通过 `plugins/labflow/agents/learning-worker.toml` 安装的自定义子代理。该角色尚未安装时，内置 `worker` 的启动提示需要加载 `learning-forensics`，写明阶段与视角，携带完整委派格式，并重申盲审输入、隐藏写入、有界探针和返回合同。返回的线程句柄写入 `.learning/state/workers.json`。

盲审返回后按机制、证据和反证做冲突表，不按同意人数投票。相关问题优先续接原任务；`cross-examination`（交叉质询）阶段可以显式提供竞争证据。

当独立 workers 指向同一个 decisive probe、活跃不确定性已收缩到少数因果链接，或新增返回只会重复已知证据时，停止增加 lanes。

</parallel_investigation>

<adaptive_operation>

## 首轮后动态调整强度

- **focused / lite：** 只续接或启动仍有实质信息增益的 1–3 条 learning-worker lanes，常规评估、综合和 probe 转由主代理负责；
- **primary-led convergence：** 主代理拥有全部实验和决定；`learning-worker` 仍可提供独立因果挑战，`explore-worker` 可承担源码、artifact、文档和外部来源等有界 read-heavy 检索；
- **re-expansion：** 新的矛盾证据打开另一条因果分支时，在同一 dossier 内增加新相关且不重复的 lanes，不重启 dossier，也不机械重跑原始首轮。

这些是随证据变化的调查阶段，不是用户启动时选择的固定模式，也不是只能升级的单向状态机。证据收缩后立即降级；只有新区别会改变决定时才重新扩展。`learning-worker` 负责因果分析，`explore-worker` 负责检索支持，两者不互相替代。

</adaptive_operation>

<probe_and_tuning>

探针优先选择高预期信息增益、低计算成本、低时间、低代码侵入和低污染风险的方案。需要数值排序时，先把各项归一化为当前案例内的无量纲评分：

$$\large
S=\frac{\widehat I}{\epsilon+w_c\widehat C+w_t\widehat T+w_r\widehat R+w_x\widehat X}
$$

优先使用公式检查、固定批次审计、小样本过拟合、冻结模块读取器、oracle（真值）特征、干预/打乱、梯度方向一致性、匹配优化器对照和冻结总体评估。

可执行 probe 默认由主代理编写、启动、观察和迭代。可在普通工具超时内完成的命令使用 bounded shell；长时、交互式、实时或需要正式跟踪的进程使用 PTY/后台会话。独立探针并行前检查 CPU、GPU 显存、RAM、磁盘、输出隔离与预计时长，在不超额争用资源的前提下分配最大有效并行波次。

只有保持 worker blindness 或 lane-local context 对诊断有实质价值、且 probe 可安全自包含时，才让原 learning-worker 进入 `phase: probe`。此时声明真假预测、输入、冻结证据、隔离写入路径、600 秒上限、最多一个 GPU 进程和停止条件。worker 使用普通 shell 硬超时，所有文件写入 `.learning/probes/<probe-id>/`；项目源码变更以提案返回，PTY、正式运行、检查点、缓存和正式训练预算继续由主代理拥有。

长时间或正式实验由主代理拥有。启动前询问用户，保存版本化科学配置和独立输出目录。OpenCode 有 PTY/后台会话工具时遵守全局规则；Codex 使用宿主原生后台能力。通用子代理继续承担证据工作，进程完成依靠后台工具的原生通知。

</probe_and_tuning>

<synthesis_and_reporting>

结论指出当前证据支持的最早断点、仍然竞争的一小组断点，或由于缺少关键量而不可辨识，并区分局部拟合能力、优化、总体学习、泛化、迁移和系统性能。

主代理写 `overview.md`、动态 `topics/*.md` 和可选 `assets/`，只为本案例真正重要的维度形成完整论文式报告。子代理写 `.learning/audit/lanes/` 与 `.learning/probes/` 授权文件；主代理拥有中央状态、交叉质询、决策树、过程记录和所有人类可见文件。

只在信息承载节点更新 dossier：新 sealed snapshot、决定性 worker return、完成的 probe、改变后的因果边界或已接受决定。不要把每条命令、PTY 状态变化和中间想法都变成强制维护动作。

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
> 把查看 skill 当作自动正式启动、通用超参数清单、偏好假设广播、语义重复的并行任务、证据收缩后仍维持全面委派、以子代理投票代替证据、脱离基线和统计总体解释原始损失、用梯度大小代替信息质量、普通漂移就创建新 dossier、把 primary-owned PTY 绕给 worker，以及过早运行正式预算，都会降低定位最早断点的效率。

</common_drift>
