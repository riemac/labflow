# labflow

Codex-native scientific research coding skill toolbox.

labflow provides reusable skills for research-heavy coding work in Codex:

- Local codebase research with semantic search, `rg`, key-file reads, and read-heavy subagent delegation.
- External research over official docs, upstream source, papers, and version-specific evidence.
- Design scaffolding that turns ideas into reviewable interfaces, fields, docs, and TODO anchors.
- Engineering handoff snapshots written only to an explicitly specified path.
- Git task flow for task boundaries, commits, history review, and GitHub publishing mechanics.
- Scientific annotation, pseudocode drafting, PDF reading, Obsidian CLI operations, and self-update.
- Background agents for read-heavy local exploration and external research.
- MCP configuration for `pdf-reader`, `augmentcode`, and `context7`.

The old GitHub Copilot plugin version is preserved on the `copilot-legacy` branch. The `main` branch targets Codex only.

## Layout

```text
.agents/plugins/marketplace.json
plugins/labflow/
├── .codex-plugin/plugin.json
├── .mcp.json
├── agents/
├── prompts/
└── skills/
```

## Install Or Reload

From this repository:

```bash
codex plugin marketplace add /home/hac/labflow
```

If Codex reports that the marketplace already exists, follow the CLI's suggested upgrade command.

`context7` expects `CONTEXT7_API_KEY` to be present in the shell environment before starting Codex. The other configured MCP servers use local commands:

- `npx @sylphx/pdf-reader-mcp`
- `auggie --mcp --mcp-auto-workspace`
- `npx @upstash/context7-mcp@1.0.30`

## Use In VS Code Codex

Install or reload the marketplace, then use the plugin by naming the skill in the Codex chat inside any project:

- `使用 codebase-research 调研相机配置链路`
- `使用 external-research 查 IsaacLab 官方相机 API`
- `使用 design-scaffold 把这个扰动配置 idea 落成接口草图和字段说明`
- `使用 engineering-handoff 更新 vault=Research path=_progress.md`
- `使用 git-task-flow 提交并推送当前任务`

Codex may also trigger these skills automatically when the request clearly matches their descriptions.

## Prompts And Background Agents

`prompts/lab.md` and `prompts/labprompt.md` are kept as optional manual reference prompts. They are not the primary plugin interface.

`agents/lab-explore.md` and `agents/lab-research.md` are read-heavy background agent templates. They are not top-level agents; the main Codex session can delegate local code exploration or external evidence gathering to them when that saves context.

## Engineering Handoff

Use `engineering-handoff` only when you explicitly provide a target path, for example:

```text
vault=Research path=_progress.md
```

The handoff records engineering state only: current goal, progress, unfinished steps, key files, validation state, and blockers. Research context remains manually maintained by the user.
