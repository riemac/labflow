# labflow

Cross-platform scientific research coding skill toolbox for Codex and OpenCode.

labflow provides reusable skills for research-heavy coding work:

- Stage-driven discussion hooks for lightweight idea refinement and goal clarification.
- Local codebase research with replaceable semantic/code-RAG retrieval, `tree`/`fd`/`rg`, key-file reads, and read-heavy subagent delegation.
- External research over official docs, upstream source, papers, and version-specific evidence.
- Deep research reports for complex cross-source feasibility and architecture questions.
- First-principles research brainstorming with method cards, assumptions, counterexamples, and minimal validation probes.
- Learning forensics for tracing failed behavior through a case-specific causal chain, coordinating hypothesis-blind parallel workers, and selecting high-information probes before formal tuning.
- Design-scaffold stage for turning mature ideas into reviewable interfaces, fields, docs, and TODO anchors.
- Git task flow for task boundaries, commits, history review, and GitHub publishing mechanics.
- Scientific annotation, PDF reading, Obsidian CLI operations, and self-update.
- Background agents for read-heavy exploration, external research, and bounded learning-system diagnosis.
- MCP configuration for `pdf-reader`.

The old GitHub Copilot plugin version is preserved on the `copilot-legacy` branch. The `main` branch carries both the Codex plugin and the OpenCode integration.

## Layout

```text
.agents/plugins/marketplace.json
plugins/labflow/
├── .codex-plugin/plugin.json
├── .mcp.json
├── agents/
├── hooks/
├── prompts/
└── skills/
opencode/
├── agents/
├── config/
├── plugins/
└── skills/
```

## Install Or Reload

From this repository, use the reload helper so the marketplace, plugin cache, and `learning-worker` custom-agent link are updated together:

```bash
/home/hac/labflow/plugins/labflow/skills/self-update/scripts/reload_labflow_plugin.sh
```

The helper preserves any user-owned `~/.codex/agents/learning-worker.toml`. When that path is free, it links the tracked Labflow template. Manual marketplace remove/add remains available, but it installs skills only and leaves the custom agent to the built-in-worker fallback.

External library/API docs are handled by ctx7 CLI skills, not an MCP server. The configured MCP server uses a local command:

- `npx @sylphx/pdf-reader-mcp`

## Stage-Driven Development

Labflow includes a lightweight stage runtime for nonlinear research work. Start a stage with Codex plugin-prefixed skill commands:

- `$labflow:stage-idea-refine`: discuss research ideas, assumptions, routes, and risks.
- `$labflow:stage-goal-clarify`: clarify goal, scope, non-goals, and acceptance checks.
- `$labflow:stage-design-scaffold`: write mature design intent into distributed TODOs, docs, and interface anchors.
- `$labflow:stage-control pass`: mark the current stage as passed.
- `$labflow:stage-control cancel`: cancel the current stage.
- `$labflow:stage-control status`: inspect current stage state.

Bare `$stage-*` tokens are intentionally not stage-entry commands; this avoids accidental activation when discussing hook names or file paths.

Stage state is stored under the active project at `.codex/labflow-stage/` and scoped by Codex session, so parallel conversations in the same repository do not inherit each other's stage.

Plugin-bundled hooks are opt-in in Codex. Check or enable the required feature flag with:

```bash
python3 /home/hac/labflow/plugins/labflow/skills/stage-control/scripts/check_stage_hooks.py --check
python3 /home/hac/labflow/plugins/labflow/skills/stage-control/scripts/check_stage_hooks.py --write
```

The hook uses only Python standard-library modules. When a stage starts, it best-effort opens a Ghostty `+new-window` HUD; if Ghostty is unavailable or `LABFLOW_STAGE_HUD_DISABLED=1` is set, stage context injection still works normally.

After changing Labflow itself, use:

```bash
/home/hac/labflow/plugins/labflow/skills/self-update/scripts/reload_labflow_plugin.sh
```

## Use In VS Code Codex

Install or reload the marketplace, then use the plugin by naming the skill in the Codex chat inside any project:

- `$labflow:stage-idea-refine 讨论这个研究 idea`
- `$labflow:stage-goal-clarify 明确验收标准`
- `$labflow:stage-design-scaffold 把成熟设计沉淀成分布式 TODO、字段说明和接口锚点`
- `使用 codebase-research 调研相机配置链路`
- `使用 external-research 查 IsaacLab 官方相机 API`
- `使用 deep-research 调研 IsaacLab 是否支持异构资产并行训练`
- `使用 research-brainstorm 从第一性原理手撕这个研究 idea 并给出候选方法卡片`
- `使用 learning-forensics 调查这次训练为什么没有学会，并定位最早断点`
- `使用 git-task-flow 提交并推送当前任务`

Codex may also trigger these skills automatically when the request clearly matches their descriptions.

## Prompts And Background Agents

`prompts/lab.md` and `prompts/labprompt.md` are kept as optional manual reference prompts. They are not the primary plugin interface.

`agents/lab-explore.md` and `agents/lab-research.md` are legacy read-heavy templates. `agents/learning-worker.toml` follows Codex's custom-agent schema; the reload helper links it into `~/.codex/agents/` without replacing a user-owned file. The main session delegates bounded evidence work while retaining scientific decisions and human-facing synthesis.
