---
name: autopilot
description: "仅当用户明确要求 autopilot、auto、autoresearch、无人值守、过夜或长程自主迭代时使用。创建或接管一个持续 Goal，依靠原生 TODO、PTY、Git 和真实产物自适应执行，并按结果类型使用 Research、Coding 或 Paper profile。仅用于 OpenCode。"
---

# Autopilot

Autopilot 是用户明确授权的 OpenCode 长程执行模式，不是 primary agent、固定流水线、文档维护工作流，也不允许静默扩权。

<activation_contract>

只有“开始 auto 吧”“启动 autoresearch”“无人值守执行”等明确表达才激活。若 decision-complete Plan 已经形成，随后一次明确启动就足够，不重复确认。启动前先读取可发现的项目事实；只有缺失的高影响边界会导致跑错目标或不安全时，才聚合询问一次。

当前为 `plan` 或 `labflow-plan` 时保持只读，只提供交接；用户切回可执行 primary agent 后才能设置或恢复 Goal 并开始工作。执行后不以日常可逆问题打断工作，采用保守且有用的选择继续取证；不可逆选择、缺少授权、危险动作或必须由人决定的事项用 `goal_block` 停止。

</activation_contract>

<flipped_preflight>

把用户最初的表述视为动机、症状、方向或希望发生的变化，不机械当成最终目标。读取项目和证据后，用简洁自然语言回译当前最佳理解：真正要实现什么、为什么重要、成功与失败或反证如何区分、哪些决定和 non-goals 已固定、哪些属于方法自由，以及哪里需要人类判断或副作用授权。

把目标不确定性与方法不确定性分开。目标不确定性在启动前协作解决；实现路线、实验设计、架构、超参数、候选筛选和工作分解保持自适应，除非它们改变目标或授权边界。

</flipped_preflight>

<goal_ownership>

改变 Goal 前先调用 `goal_status`：

- 没有 Goal：调用一次 `goal_set`，写入简洁但完整的总目标、成功标准、关键约束和 `mode: normal`。批准 Plan 明确指定单次限制时再传入；否则不覆盖，让全局 `maxTurns`、`maxDurationMs` 和 `maxTokens` 生效。
- 当前 Goal 就是同一任务：保留它。只有 objective 或当前重点实质过时时才调用 `update_goal`；只有用户授权继续自主工作时才 `goal_resume`。
- 当前 Goal 不同或归属不明：不得静默替换或清除，在启动前解决冲突，或用 `goal_block` 报告。

Goal 的 objective、success criteria 和 constraints 在 active 期间每次模型请求都可见。内容应保持高信号，只写稳定总目标、当前决定性重点、证据边界和重要限制，不塞入工作日志、命令历史或整份项目文档。

不要每条命令或小步骤后更新 Goal。只有发生重要 pivot、用户实质改向，或旧重点已闭合而新重点开始主导工作时才更新 objective；普通进展保留同一个 Goal。默认只使用一个 focused Goal，除非用户明确要求，不创建 background Goal、sequence 或切换 focus。

有意保留停止用 `goal_pause`；用户明确继续后用 `goal_resume`；具体外部或人类需求用 `goal_block`；直接验证总体目标后才调用 `goal_complete`。完成证据应列出决定性产物和检查，不只宣称完成。

</goal_ownership>

<adaptive_execution>

不创建 phase 文档，持续执行轻量证据循环：

1. 读取 Goal、TODO、项目规则、Git 状态、活动 PTY 或其他工作以及真实产物。
2. 选择信息增益或成功边界推进价值最高的下一步。
3. 路线明确时直接执行；只有真实不确定性值得时才比较机制不同的候选。
4. 先做最小决定性检查，证据与资源允许时再扩大测试或实验。
5. 整合有效结果，放弃自己创建的失败路线而不碰既有工作，并在有恢复价值时保存验证过的 checkpoint。
6. 只有主导重点或边界变化时更新 Goal，否则直接继续工作。

运行成功不等于科学有效，编译通过不等于行为验收，流畅文字也不等于论文 claim 有证据。

</adaptive_execution>

<native_state>

Goal 保存稳定结果、当前重点、约束和完成状态；`todowrite` 在有价值时管理可执行多步工作；`pty_list` 与完成通知保存长进程状态；Git 保存源码历史和恢复边界；测试、日志、checkpoint、图表、论文、数据等真实产物保存任务证据。

不创建 `.autopilot/`、固定 Auto 日志、合同、manifest、phase record 或交接文档。只有用户要求、项目规则要求、已有文档因改动实质过期，或任务本身需要持久科研/工程产物时，才创建或更新对应项目文档；文档更新放在自然工作边界，不为了叙述进度暂停有用工作。

Compact 或恢复后调用 `goal_status`，检查 TODO、PTY、Git 和真实产物，从下一个未完成具体步骤继续；不能因为对话记忆不完整而重复启动任务。

</native_state>

<maximum_useful_parallelism>

追求最大有效并行，不追求最大进程数。只有独立 lane 能实质节省时间或降低路线偏见时才并行；明确的局部路线优先直接执行。每条 lane 必须有真正不同的问题、机制或隔离输出，主 Agent 保留整合和最终判断。

不确定路线不要过早押注一个答案；保留少量机制不同的候选，用最便宜的决定性证据筛除。不要制造表面变体，也不要并行重复检索同一个偏好答案。

昂贵实验前估计 GPU、VRAM、CPU、RAM、磁盘、墙钟和产物体积；峰值或语义不确定时先运行代表性 canary，前置证据通过后再扩容。

</maximum_useful_parallelism>

<event_driven_work>

短任务用普通有界命令，长时、交互或正式过程用 PTY。PTY 使用正确 project-local workdir、明确标题、`notifyOnExit: true` 和适用的自然 timeout，禁止 sleep/poll。Goal-PTY adapter 只等待同 session 中正在运行或停止的 notifying PTY；PTY 退出后检查有界结果、保留有效产物、结束当前 turn，再由 idle 恢复 Goal continuation。

</event_driven_work>

<human_interruption>

用户消息优先并通常暂停 Goal。先回答用户；若用户说明只是询问并明确授权 Auto 继续，则恢复同一个 Goal。若目标或限制改变，在语义仍连贯时更新同一 Goal；只有用户实质替换任务时才创建新 Goal。没有继续授权就保持暂停。

</human_interruption>

<profiles>

按主要结果读取一个 profile：科研/算法结论与实验可行性用 `references/research.md`；正确、可维护、验证过的软件行为用 `references/coding.md`；证据对齐的论文与投稿产物用 `references/paper.md`。Profile 只指导证据和执行，不要求额外状态文件；混合任务可以借用其他 profile 的方法，不增加工作流层。

</profiles>

<workflow_map>

```mermaid
flowchart TD
    A[用户明确启动 Auto] --> B[读取事实并回译真正目标]
    B --> C{当前 Goal 是否匹配?}
    C -- 没有 Goal --> D[goal_set 一次]
    C -- 同一任务 --> E[保留或实质更新 Goal]
    C -- 冲突 --> F[解决冲突或 goal_block]
    D --> G[自适应证据驱动执行]
    E --> G
    G --> H{总体结果已验证?}
    H -- 否 --> G
    H -- 人类决定或阻塞 --> I[goal_pause 或 goal_block]
    H -- 是 --> J[携带证据 goal_complete]
```

</workflow_map>

<stop_and_handoff>

在验证完成、用户暂停、预算耗尽、安全边界、具体外部阻塞或已无可辩护路线时停止。把最强支持结论、反证、有保留价值的失败路线、真实产物和复现检查写入任务自然承载面。

保护无关 dirty changes，不 reset、clean、stash 或覆盖不属于本任务的工作。除非用户或批准 Plan 明确授权，不 bump、建 release tag、push、发布、部署、发送外部消息、购买资源、轮换凭据或修改生产环境。

</stop_and_handoff>
