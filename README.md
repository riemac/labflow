# labflow

Codex-native scientific research workflow plugin.

labflow provides a lightweight research operating layer for Codex:

- Obsidian-backed project memory through `_context.md`, `_progress.md`, `ideas/`, and `tasks/`.
- Top-level launch prompts for `Lab` and `LabPrompt`.
- Background agents for local code exploration and external research.
- Skills for scientific annotation, pseudocode drafting, PDF reading, Obsidian operations, handoff, and self-update.
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
├── scripts/
└── skills/
```

## Install Or Reload

From this repository:

```bash
codex plugin marketplace add /home/hac/labflow-codex
```

If Codex reports that the marketplace already exists, follow the CLI's suggested upgrade command.

`context7` expects `CONTEXT7_API_KEY` to be present in the shell environment before starting Codex. The other configured MCP servers use local commands:

- `npx @sylphx/pdf-reader-mcp`
- `auggie --mcp --mcp-auto-workspace`
- `npx @upstash/context7-mcp@1.0.30`

## Start A Lab Session

From any research project:

```bash
/home/hac/labflow-codex/plugins/labflow/scripts/codex-lab
```

Pass an initial request if useful:

```bash
/home/hac/labflow-codex/plugins/labflow/scripts/codex-lab "继续上次的 reward shaping 任务"
```

## Start A LabPrompt Session

Use LabPrompt as a separate Codex window/session for turning rough ideas into a natural execution prompt:

```bash
/home/hac/labflow-codex/plugins/labflow/scripts/codex-labprompt "我想重构一下相机观测，但还没想清楚"
```

Set `LABFLOW_PROJECT_DIR=/abs/project` if you want the launcher to start Codex in a different project directory.

## Vault Contract

Each research project can define `.labflow`:

```text
vault=<Obsidian vault name>
vault_path=<absolute vault path>
```

The vault remains the only durable research memory:

- `_context.md` is a short research snapshot and is overwritten at handoff.
- `_progress.md` is an engineering handoff snapshot and is overwritten at handoff.
- `_progress-history.md` is append-only changelog.
- `ideas/` stores hypothesis/question/finding/decision atoms.
- `tasks/` stores LabPrompt-authored task briefs for human navigation.
