# labflow

Codex-native scientific research coding skill toolbox.

labflow provides reusable skills for research-heavy coding work in Codex:

- Stage-driven discussion hooks for lightweight idea refinement and goal clarification.
- Local codebase research with semantic search, `rg`, key-file reads, and read-heavy subagent delegation.
- External research over official docs, upstream source, papers, and version-specific evidence.
- Design scaffolding that turns ideas into reviewable interfaces, fields, docs, and TODO anchors.
- Git task flow for task boundaries, commits, history review, and GitHub publishing mechanics.
- Scientific annotation, PDF reading, Obsidian CLI operations, and self-update.
- Background agents for read-heavy local exploration and external research.
- MCP configuration for `pdf-reader` and `augmentcode`.

The old GitHub Copilot plugin version is preserved on the `copilot-legacy` branch. The `main` branch targets Codex only.

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
```

## Install Or Reload

From this repository:

```bash
codex plugin marketplace remove riemac
codex plugin marketplace add /home/hac/labflow
codex plugin remove labflow@riemac
codex plugin add labflow@riemac
```

For local directory marketplaces, refresh both the marketplace source and the installed plugin cache. A plain marketplace `add` may only report that the marketplace already exists.

External library/API docs are handled by ctx7 CLI skills, not an MCP server. The configured MCP servers use local commands:

- `npx @sylphx/pdf-reader-mcp`
- `auggie --mcp --mcp-auto-workspace`

## Stage-Driven Development

Labflow includes a lightweight stage runtime for nonlinear research work. Start a stage by naming a stage skill or command in Codex:

- `$stage-idea-refine`: discuss research ideas, assumptions, routes, and risks.
- `$stage-goal-clarify`: clarify goal, scope, non-goals, and acceptance checks.
- `$stage-pass`: mark the current stage as passed.
- `$stage-cancel`: cancel the current stage.
- `$stage-status`: inspect current stage state.

Stage state is stored in the active project at `.codex/labflow-stage/state.json`.

Plugin-bundled hooks are opt-in in Codex. Check or enable the required feature flag with:

```bash
python3 /home/hac/labflow/plugins/labflow/skills/stage-control/scripts/check_stage_hooks.py --check
python3 /home/hac/labflow/plugins/labflow/skills/stage-control/scripts/check_stage_hooks.py --write
```

The hook uses only Python standard-library modules. When a stage starts, it best-effort opens a Ghostty `+new-window` HUD; if Ghostty is unavailable, stage context injection still works normally.

After changing Labflow itself, use:

```bash
/home/hac/labflow/plugins/labflow/skills/self-update/scripts/reload_labflow_plugin.sh
```

## Use In VS Code Codex

Install or reload the marketplace, then use the plugin by naming the skill in the Codex chat inside any project:

- `使用 stage-idea-refine 讨论这个研究 idea`
- `使用 stage-goal-clarify 明确验收标准`
- `使用 codebase-research 调研相机配置链路`
- `使用 external-research 查 IsaacLab 官方相机 API`
- `使用 design-scaffold 把这个扰动配置 idea 落成接口草图和字段说明`
- `使用 git-task-flow 提交并推送当前任务`

Codex may also trigger these skills automatically when the request clearly matches their descriptions.

## Prompts And Background Agents

`prompts/lab.md` and `prompts/labprompt.md` are kept as optional manual reference prompts. They are not the primary plugin interface.

`agents/lab-explore.md` and `agents/lab-research.md` are read-heavy background agent templates. They are not top-level agents; the main Codex session can delegate local code exploration or external evidence gathering to them when that saves context.
