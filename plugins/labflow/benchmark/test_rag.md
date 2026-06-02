# Questions listed for RAG

这里列出了一些针对 RAG（Retrieval-Augmented Generation）的测试问题，这些问题旨在评估 RAG 模型在不同场景下的表现。

## IsaacLab

这些问题默认以 `/home/hac/isaac` 为检索根目录，重点测试 CocoIndex / 其他本地 RAG 工具能否在 `IsaacLab/` 代码库内找回正确入口。`Expected hit area` 不是唯一答案，只是人工评估时的参考证据区域。

建议评估时记录：

- `Top-1 / Top-3 / Top-10` 是否命中 `Expected hit area`。
- 命中的是文档、示例脚本、核心实现、测试，还是无关噪音。
- 查询耗时、是否需要限制目录、是否需要换英文关键词。
- 对中文或中英混合查询，额外记录是否能跨语言找回英文源码/文档。

推荐同时跑两种模式：

- IsaacLab-only：`ccc search --path 'IsaacLab/**' "<question>"`，评估单项目内语义召回。
- Full workspace：`ccc search "<question>"`，评估 `/home/hac/isaac` 根索引下的跨仓库抗噪声能力。

### Quick Smoke

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-SMOKE-001 | How to add a tactile sensor to a robot fingertip in IsaacLab? | `IsaacLab/docs/source/overview/core-concepts/sensors/visuo_tactile_sensor.rst`, `IsaacLab/scripts/demos/sensors/tacsl_sensor.py`, `IsaacLab/source/isaaclab_contrib/isaaclab_contrib/sensors/` | Natural-language sensor discovery |
| IL-SMOKE-002 | Where is the example for adding sensors on a robot, including contact or frame transformer sensors? | `IsaacLab/scripts/tutorials/04_sensors/add_sensors_on_robot.py`, `IsaacLab/docs/source/tutorials/04_sensors/` | Tutorial/example recall |
| IL-SMOKE-003 | Which files explain how to register a new Gym RL environment in IsaacLab? | `IsaacLab/docs/source/tutorials/03_envs/register_rl_env_gym.rst`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/` | Docs + source registration path |
| IL-SMOKE-004 | How do I wrap an IsaacLab environment for rl_games, rsl_rl, skrl, or stable-baselines3 training? | `IsaacLab/docs/source/how-to/wrap_rl_env.rst`, `IsaacLab/source/isaaclab_rl/isaaclab_rl/`, `IsaacLab/scripts/reinforcement_learning/` | RL framework bridge discovery |

### Environment And Task Registration

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-ENV-001 | How are ManagerBasedRLEnv tasks structured and configured in IsaacLab? | `IsaacLab/source/isaaclab/isaaclab/envs/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/manager_based/`, `IsaacLab/docs/source/tutorials/03_envs/create_manager_rl_env.rst` | Architecture-level semantic recall |
| IL-ENV-002 | What is the difference between a DirectRLEnv and a ManagerBasedRLEnv in IsaacLab? | `IsaacLab/docs/source/tutorials/03_envs/create_direct_rl_env.rst`, `IsaacLab/docs/source/tutorials/03_envs/create_manager_base_env.rst`, `IsaacLab/source/isaaclab/isaaclab/envs/` | Comparative concept retrieval |
| IL-ENV-003 | Where are observations, rewards, terminations, events, and curriculum terms registered for manager-based tasks? | `IsaacLab/source/isaaclab/isaaclab/managers/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/manager_based/**/mdp/`, `IsaacLab/docs/source/api/lab/isaaclab.envs.mdp.rst` | MDP manager component discovery |
| IL-ENV-004 | How does IsaacLab list all registered environments from the command line? | `IsaacLab/scripts/environments/list_envs.py`, `IsaacLab/docs/source/overview/environments.rst` | Script entry-point retrieval |
| IL-ENV-005 | Where is the random agent script for smoke-testing an IsaacLab task? | `IsaacLab/scripts/environments/random_agent.py`, `IsaacLab/docs/source/overview/simple_agents.rst` | Operational script recall |
| IL-ENV-006 | How can a task export or define IO descriptors for policy deployment? | `IsaacLab/scripts/environments/export_IODescriptors.py`, `IsaacLab/docs/source/policy_deployment/01_io_descriptors/` | Policy deployment context retrieval |

### Sensors

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-SENSOR-001 | How is the ContactSensor configured and demonstrated in IsaacLab? | `IsaacLab/source/isaaclab/isaaclab/sensors/contact_sensor/`, `IsaacLab/scripts/demos/sensors/contact_sensor.py`, `IsaacLab/docs/source/api/lab/isaaclab.sensors.rst` | Class + demo retrieval |
| IL-SENSOR-002 | How do I attach a frame transformer sensor to robot links and read relative transforms? | `IsaacLab/source/isaaclab/isaaclab/sensors/frame_transformer/`, `IsaacLab/scripts/tutorials/04_sensors/run_frame_transformer.py` | Sensor-specific API recall |
| IL-SENSOR-003 | Where is the RayCaster or RayCasterCamera sensor configured and demonstrated? | `IsaacLab/source/isaaclab/isaaclab/sensors/ray_caster/`, `IsaacLab/scripts/demos/sensors/raycaster_sensor.py`, `IsaacLab/scripts/tutorials/04_sensors/run_ray_caster.py` | Similar-name sensor disambiguation |
| IL-SENSOR-004 | How do tiled cameras differ from normal USD cameras in IsaacLab examples? | `IsaacLab/source/isaaclab/isaaclab/sensors/camera/`, `IsaacLab/scripts/demos/sensors/cameras.py`, `IsaacLab/scripts/benchmarks/benchmark_cameras.py` | Conceptual + benchmark retrieval |
| IL-SENSOR-005 | Where is the IMU sensor example and configuration in IsaacLab? | `IsaacLab/source/isaaclab/isaaclab/sensors/imu/`, `IsaacLab/scripts/demos/sensors/imu_sensor.py` | Direct example lookup |

### Assets, Spawning, And Simulation

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-ASSET-001 | How do I define an ArticulationCfg for a new robot in IsaacLab? | `IsaacLab/docs/source/how-to/write_articulation_cfg.rst`, `IsaacLab/scripts/tutorials/01_assets/add_new_robot.py`, `IsaacLab/source/isaaclab_assets/isaaclab_assets/robots/` | Asset config pattern retrieval |
| IL-ASSET-002 | How can I import or convert a URDF robot asset into IsaacLab? | `IsaacLab/docs/source/how-to/import_new_asset.rst`, `IsaacLab/scripts/tools/convert_urdf.py`, `IsaacLab/source/isaaclab/isaaclab/sim/converters/` | Tool + converter recall |
| IL-ASSET-003 | Where are rigid object, deformable object, and articulation asset classes implemented? | `IsaacLab/source/isaaclab/isaaclab/assets/`, `IsaacLab/scripts/tutorials/01_assets/` | Asset class hierarchy retrieval |
| IL-ASSET-004 | How does IsaacLab spawn multiple assets or randomize asset instances in a scene? | `IsaacLab/docs/source/how-to/multi_asset_spawning.rst`, `IsaacLab/scripts/demos/multi_asset.py`, `IsaacLab/source/isaaclab/isaaclab/sim/spawners/` | Scene spawning workflow |
| IL-ASSET-005 | How do I make a fixed prim or fixed asset in IsaacLab? | `IsaacLab/docs/source/how-to/make_fixed_prim.rst`, `IsaacLab/source/isaaclab/isaaclab/sim/schemas/` | Narrow how-to retrieval |
| IL-SIM-001 | Where is AppLauncher used to start Isaac Sim from IsaacLab scripts? | `IsaacLab/source/isaaclab/isaaclab/app/`, `IsaacLab/scripts/tutorials/00_sim/launch_app.py`, `IsaacLab/scripts/demos/` | Common runtime bootstrap retrieval |
| IL-SIM-002 | How do I configure rendering mode or camera output saving in IsaacLab? | `IsaacLab/docs/source/how-to/configure_rendering.rst`, `IsaacLab/docs/source/how-to/save_camera_output.rst`, `IsaacLab/scripts/tutorials/00_sim/set_rendering_mode.py` | Rendering docs retrieval |

### Scene, Terrain, And Managers

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-SCENE-001 | How is InteractiveScene configured and cloned across many environments? | `IsaacLab/source/isaaclab/isaaclab/scene/`, `IsaacLab/scripts/tutorials/02_scene/create_scene.py` | Scene abstraction retrieval |
| IL-SCENE-002 | Where is terrain generation configured, including procedural terrain demos? | `IsaacLab/source/isaaclab/isaaclab/terrains/`, `IsaacLab/scripts/demos/procedural_terrain.py`, `IsaacLab/docs/source/api/lab/isaaclab.terrains.rst` | Terrain subsystem recall |
| IL-MANAGER-001 | How does the RewardManager compute reward terms from RewTerm configs? | `IsaacLab/source/isaaclab/isaaclab/managers/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/**/mdp/rewards.py` | Config-to-runtime data flow |
| IL-MANAGER-002 | How does the ObservationManager group observation terms and concatenate tensors? | `IsaacLab/source/isaaclab/isaaclab/managers/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/**/mdp/observations.py` | Manager behavior retrieval |
| IL-MANAGER-003 | How are EventTerm and reset/randomization events applied in manager-based environments? | `IsaacLab/source/isaaclab/isaaclab/managers/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/**/mdp/events.py` | Event pipeline retrieval |
| IL-MANAGER-004 | Where does IsaacLab implement action managers and action term processing? | `IsaacLab/source/isaaclab/isaaclab/managers/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/**/mdp/actions.py` | Action pipeline retrieval |

### Reinforcement Learning And Training Scripts

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-RL-001 | How do I train an IsaacLab task with rl_games from the command line? | `IsaacLab/scripts/reinforcement_learning/rl_games/train.py`, `IsaacLab/source/isaaclab_rl/isaaclab_rl/rl_games/`, `IsaacLab/docs/source/overview/reinforcement-learning/` | Training entry-point retrieval |
| IL-RL-002 | How do I train or play a policy with rsl_rl in IsaacLab? | `IsaacLab/scripts/reinforcement_learning/rsl_rl/train.py`, `IsaacLab/scripts/reinforcement_learning/rsl_rl/play.py`, `IsaacLab/source/isaaclab_rl/isaaclab_rl/rsl_rl/` | Framework-specific recall |
| IL-RL-003 | Where are command-line arguments for rsl_rl parsed and mapped into configs? | `IsaacLab/scripts/reinforcement_learning/rsl_rl/cli_args.py`, `IsaacLab/source/isaaclab_rl/isaaclab_rl/rsl_rl/` | CLI-to-config data flow |
| IL-RL-004 | How does IsaacLab launch Ray Tune or Ray jobs for reinforcement learning? | `IsaacLab/scripts/reinforcement_learning/ray/`, `IsaacLab/docs/source/features/ray.rst` | Distributed training retrieval |
| IL-RL-005 | Where are performance benchmark scripts for RL and non-RL environments? | `IsaacLab/scripts/benchmarks/benchmark_rlgames.py`, `IsaacLab/scripts/benchmarks/benchmark_rsl_rl.py`, `IsaacLab/scripts/benchmarks/benchmark_non_rl.py` | Benchmark script recall |

### Imitation Learning And Data Tools

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-IL-001 | How does IsaacLab Mimic generate datasets from demonstrations? | `IsaacLab/source/isaaclab_mimic/isaaclab_mimic/`, `IsaacLab/scripts/imitation_learning/isaaclab_mimic/generate_dataset.py`, `IsaacLab/docs/source/overview/imitation-learning/` | Multi-package retrieval |
| IL-IL-002 | Where are HDF5 replay, recording, and conversion tools implemented? | `IsaacLab/scripts/tools/replay_demos.py`, `IsaacLab/scripts/tools/record_demos.py`, `IsaacLab/scripts/tools/hdf5_to_mp4.py`, `IsaacLab/scripts/tools/mp4_to_hdf5.py` | Tooling recall |
| IL-IL-003 | How do robomimic training and play scripts integrate with IsaacLab data? | `IsaacLab/scripts/imitation_learning/robomimic/`, `IsaacLab/docs/source/overview/imitation-learning/` | External framework bridge |

### Debugging And Edge Cases

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-DBG-001 | Where does IsaacLab document troubleshooting for installation, rendering, or simulation problems? | `IsaacLab/docs/source/refs/troubleshooting.rst`, `IsaacLab/docs/source/setup/installation/` | Documentation retrieval |
| IL-DBG-002 | How can I check whether USD assets are instanceable or convert them to instanceable assets? | `IsaacLab/scripts/tools/check_instanceable.py`, `IsaacLab/scripts/tools/convert_instanceable.py`, `IsaacLab/docs/source/how-to/optimize_stage_creation.rst` | Utility script retrieval |
| IL-DBG-003 | Where are tests for sensors, managers, assets, and envs located? | `IsaacLab/source/isaaclab/test/sensors/`, `IsaacLab/source/isaaclab/test/managers/`, `IsaacLab/source/isaaclab/test/envs/`, `IsaacLab/source/isaaclab_tasks/test/` | Test discovery |
| IL-DBG-004 | Which files explain migration from Orbit, IsaacGymEnvs, or OmniIsaacGymEnvs? | `IsaacLab/docs/source/migration/` | Migration docs retrieval |

### Chinese And Mixed-Language Queries

这组更接近真实使用场景：用户用中文描述意图，但希望系统找回英文文件名、英文文档和 Python 实现。

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-ZH-001 | IsaacLab 里怎么给机器人 fingertip 加 tactile sensor？ | `IsaacLab/docs/source/overview/core-concepts/sensors/visuo_tactile_sensor.rst`, `IsaacLab/scripts/demos/sensors/tacsl_sensor.py`, `IsaacLab/source/isaaclab_contrib/isaaclab_contrib/sensors/tacsl_sensor/` | Chinese-to-English semantic retrieval |
| IL-ZH-002 | manager-based 任务里 reward、observation、termination 这些 term 是在哪里配置和执行的？ | `IsaacLab/source/isaaclab/isaaclab/managers/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/manager_based/**/mdp/` | Cross-language architecture recall |
| IL-ZH-003 | 我想新建一个 IsaacLab RL 环境，Gym 注册入口和 env cfg 应该看哪些文件？ | `IsaacLab/docs/source/tutorials/03_envs/register_rl_env_gym.rst`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/` | Task registration retrieval |
| IL-ZH-004 | rsl_rl 训练脚本的命令行参数是怎么传到 agent config 里的？ | `IsaacLab/scripts/reinforcement_learning/rsl_rl/cli_args.py`, `IsaacLab/scripts/reinforcement_learning/rsl_rl/train.py`, `IsaacLab/source/isaaclab_rl/isaaclab_rl/rsl_rl/` | CLI-to-config retrieval |
| IL-ZH-005 | IsaacLab 里怎么导入 URDF 机器人并写 ArticulationCfg？ | `IsaacLab/scripts/tools/convert_urdf.py`, `IsaacLab/docs/source/how-to/import_new_asset.rst`, `IsaacLab/docs/source/how-to/write_articulation_cfg.rst` | Multi-step asset workflow |
| IL-ZH-006 | 相机传感器怎么保存输出，普通 camera 和 tiled camera 的例子在哪里？ | `IsaacLab/docs/source/how-to/save_camera_output.rst`, `IsaacLab/scripts/demos/sensors/cameras.py`, `IsaacLab/scripts/benchmarks/benchmark_cameras.py` | Similar feature disambiguation |
| IL-ZH-007 | IsaacLab 的 HDF5 demo 数据怎么录制、回放、转 mp4？ | `IsaacLab/scripts/tools/record_demos.py`, `IsaacLab/scripts/tools/replay_demos.py`, `IsaacLab/scripts/tools/hdf5_to_mp4.py`, `IsaacLab/scripts/tools/mp4_to_hdf5.py` | Toolchain retrieval |
| IL-ZH-008 | 多环境 scene clone、terrain generation、asset spawning 分别应该查哪里？ | `IsaacLab/source/isaaclab/isaaclab/scene/`, `IsaacLab/source/isaaclab/isaaclab/terrains/`, `IsaacLab/source/isaaclab/isaaclab/sim/spawners/` | Broad subsystem separation |

### Hard Architecture Queries

这组问题不只测“能不能找到一个文件”，还测检索结果能不能把文档、配置、运行时实现和示例脚本放到同一个上下文里。

| ID | Question | Expected hit area | What it tests |
| --- | --- | --- | --- |
| IL-HARD-001 | Trace the path from a manager-based task config reward term to the runtime reward tensor computation. | `IsaacLab/source/isaaclab/isaaclab/managers/reward_manager.py`, `IsaacLab/source/isaaclab/isaaclab/managers/manager_term_cfg.py`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/**/mdp/rewards.py` | Config-to-runtime trace |
| IL-HARD-002 | Trace how observations are grouped, optionally corrupted/noised, and returned to RL wrappers. | `IsaacLab/source/isaaclab/isaaclab/managers/observation_manager.py`, `IsaacLab/source/isaaclab/isaaclab/envs/`, `IsaacLab/source/isaaclab_rl/isaaclab_rl/` | Data-flow retrieval |
| IL-HARD-003 | Which files should be inspected to understand how DirectRLEnv computes actions, rewards, resets, and observations without managers? | `IsaacLab/source/isaaclab/isaaclab/envs/direct_rl_env.py`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/direct/`, `IsaacLab/docs/source/tutorials/03_envs/create_direct_rl_env.rst` | Direct env architecture |
| IL-HARD-004 | How does IsaacLab connect a robot asset cfg, scene cfg, and environment cfg for a manipulation task? | `IsaacLab/source/isaaclab_assets/isaaclab_assets/robots/`, `IsaacLab/source/isaaclab/isaaclab/scene/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/manager_based/manipulation/` | Cross-package composition |
| IL-HARD-005 | Where would I modify action scaling, joint position targets, or task-space action processing for a robot policy? | `IsaacLab/source/isaaclab/isaaclab/envs/mdp/actions/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/**/mdp/actions.py`, `IsaacLab/source/isaaclab/isaaclab/managers/action_manager.py` | Action semantics retrieval |
| IL-HARD-006 | How do sensor update periods, history buffers, and debug visualization fit into IsaacLab sensor classes? | `IsaacLab/source/isaaclab/isaaclab/sensors/sensor_base.py`, `IsaacLab/source/isaaclab/isaaclab/sensors/*/`, `IsaacLab/scripts/demos/sensors/` | Base-class plus subclass retrieval |
| IL-HARD-007 | What is the minimal set of files to inspect before adding a new robot task with training support? | `IsaacLab/docs/source/tutorials/01_assets/`, `IsaacLab/docs/source/tutorials/03_envs/`, `IsaacLab/source/isaaclab_tasks/isaaclab_tasks/`, `IsaacLab/scripts/reinforcement_learning/` | Planning-oriented retrieval |
| IL-HARD-008 | If a trained policy cannot be deployed because observations/actions do not match, where are IO descriptors and wrapper interfaces defined? | `IsaacLab/scripts/environments/export_IODescriptors.py`, `IsaacLab/docs/source/policy_deployment/01_io_descriptors/`, `IsaacLab/source/isaaclab_rl/isaaclab_rl/` | Deployment/debug retrieval |
