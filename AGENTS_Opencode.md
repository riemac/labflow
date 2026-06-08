# labflow — OpenCode Integration Development

Platform-specific guidance for editing the **OpenCode** integration.
Cross-platform conventions (skill-first, bilingual, ability vs stage, tooling,
git hygiene) live in the thin entry [AGENTS.md](AGENTS.md); read that first.

## Product shape

The integration is a single **opencode plugin** loaded via `file://` URL from
the repo. The plugin's `config` hook injects rules, the primary agent, and
skill paths — no files are copied into `~/.config/opencode/`. `install.sh` is a
first-time setup helper (adds the plugin line to `opencode.json`).

OpenCode surfaces (all under `opencode/`):

```text
opencode/
├── plugins/
│   └── labflow.ts            # plugin entry: config hook injects everything
├── labflow-rules.md          # global cross-agent rules
├── agents/
│   └── labflow-develop.md    # the single primary "develop" stage agent
├── skills/                   # adapted ability skills (de-Codex'd copies)
└── install.sh                # first-time setup: adds plugin line to opencode.json
```

The plugin appears in the opencode Plugin panel and can be toggled
with space (enable/disable) — no need to edit config files after setup.

`labflow-rules.md` carries the persona, feedback-and-discussion, and
distributed-prompting rules; it applies to every agent (build, plan,
labflow-develop) because the plugin pushes it into `cfg.instructions`, which is
additive and never shadows the user's own `AGENTS.md` or `~/.claude/CLAUDE.md`.

## Stages as agents

OpenCode has no hook-driven stage runtime. Instead:

- The **current agent is the stage**. The TUI shows the active agent name, so
  "which stage am I in" is answered natively — no HUD.
- `labflow-develop` is the single primary agent merging idea-refine + design-
  scaffold + engineering-question discussion. Switch into it (Tab) to enter the
  develop stage; switch back to **build** for implementation, **plan** for
  read-only planning.
- No per-prompt context injection: same-session history already carries the
  problem anchor, so there is no `UserPromptSubmit` equivalent.
- No state-persistence plugin: cross-session recall is left to the user.

## De-Codex mapping

When adapting a shared skill from `plugins/labflow/skills/` into
`opencode/skills/`, rewrite these Codex-isms:

| Codex | OpenCode |
|---|---|
| `$labflow:stage-*` entry / `stage-control pass` | switch primary agent (Tab) |
| `request_user_input` | `question` tool |
| `lab-explore` / `lab-research` subagents | built-in `explore` / `scout` subagents |
| stage state under `.codex/labflow-stage/` | none (agent + conversation) |
| reload codex plugin | rerun `install.sh` + restart opencode |
| `.mcp.json` manifest | `mcp` field in `opencode.json` |
| `ctx7 setup --codex` | `ctx7 setup --universal` (or `--opencode`) |

The four `stage-*` skills are not ported: their behavior is folded into
`labflow-develop`'s prompt, and stage-control is unnecessary (switching agents
is the control). pdf-read defaults to CLI / native PDF attachment with the
`pdf-reader` MCP as optional.

## Updating the OpenCode integration

OpenCode loads config/skills/agents/rules **once at startup** and does not
hot-reload. Since the plugin serves everything from the repo via `file://`,
updating means editing files in the repo and restarting opencode.

1. Work on `/home/hac/labflow` (currently the `opencode` branch).
2. Edit under `opencode/`. Shared skill source lives in
   `plugins/labflow/skills/`; the OpenCode integration uses adapted copies in
   `opencode/skills/` — keep the de-Codex mapping applied.
3. Validate changed skills:

```bash
python3 /home/hac/.codex/skills/.system/skill-creator/scripts/quick_validate.py opencode/skills/<skill-name>
```

4. If `opencode.json` changed (e.g. `mcp`), validate it:

```bash
python3 -m json.tool ~/.config/opencode/opencode.json >/dev/null
```

5. **Restart opencode** — running sessions keep the already-loaded config.

## OpenCode-specific anti-patterns

- Writing labflow rules into the user's `~/.config/opencode/AGENTS.md` (it
  shadows `~/.claude/CLAUDE.md`); use the additive `instructions` field instead.
- Re-creating a HUD or per-prompt injection; the agent name already shows the
  stage.
- Forcing a state-persistence plugin via compaction hooks unless a proven need
  appears.
- Leaving Codex-isms (`$labflow:`, `request_user_input`, `.codex/`) in adapted
  skill copies.
