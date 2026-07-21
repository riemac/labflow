# labflow — OpenCode Integration Development

Platform-specific guidance for editing the **OpenCode** integration.
Cross-platform conventions (skill-first, bilingual, ability vs stage, tooling,
git hygiene) live in the thin entry [AGENTS.md](AGENTS.md); read that first.

## Product shape

The integration is centered on a single **opencode plugin** loaded via `file://` URL from the repo. The plugin's `config` hook injects rules, primary agents, and skill paths; the same plugin also registers labflow custom tools.

OpenCode surfaces (all under `opencode/`):

```text
opencode/
├── plugins/
│   └── labflow.ts            # plugin entry: injects rules/agents/skills/tools
├── scripts/
│   └── imagegen.mjs          # OpenAI-compatible Images API CLI backend
├── labflow.json              # repo-local Image API defaults, no secrets
├── labflow.example.json      # example portable imagegen provider profile
├── package.json              # plugin runtime dependencies such as @opencode-ai/plugin
├── labflow-rules.md          # global cross-agent rules
├── agents/
│   ├── labflow-develop.md    # primary develop stage: research dialogue + scaffold
│   ├── labflow-plan.md       # primary read-only structured planning stage
│   ├── labflow-paper.md      # primary paper preparation and evidence alignment
│   └── literature-worker.md  # hidden prior-art evidence worker
├── skills/                   # adapted ability skills (de-Codex'd copies)
└── install.sh                # first-time setup: adds plugin line to opencode.json
```

The plugin appears in the opencode Plugin panel and can be toggled
with space (enable/disable) — no need to edit config files after setup.

`labflow-rules.md` carries the persona, feedback-and-discussion, and
distributed-prompting rules; it applies to every agent (build, plan,
labflow-develop, labflow-plan) because the plugin pushes it into
`cfg.instructions`, which is additive and never shadows the user's own
`AGENTS.md` or `~/.claude/CLAUDE.md`.

`imagegen` is a custom tool registered by the plugin and normally reached via
the bundled `imagegen` skill. The tool calls `opencode/scripts/imagegen.mjs`,
which uses an independent OpenAI-compatible image generation profile from repo-local
`opencode/labflow.json`, ignored `opencode/labflow.local.json`, optional
`~/.config/opencode/labflow.json`, or `OPENCODE_IMAGEGEN_*` environment
variables, with fallback to the user's configured OpenAI-compatible provider.
Keep API keys out of tracked files; use `labflow.local.json` or env for secrets.
The bundled profile reuses `provider.routin-plan` with the Responses API, so it does not duplicate the provider key.
The old `/imagegen` slash command is intentionally not installed; `install.sh`
only removes the legacy symlink when it points back into this repo.

`literature-forensics` is an OpenCode-only ability skill backed by a local Python
CLI and the hidden `literature-worker` subagent. The primary agent remains the
research lead; workers own bounded topic artifacts, while the primary persists
resumable task IDs in each project's ignored dossier state.

## Stages as agents

OpenCode has no hook-driven stage runtime. Instead:

- The **current agent is the stage**. The TUI shows the active agent name, so
  "which stage am I in" is answered natively — no HUD.
- `labflow-develop` is the nonlinear research-dialogue agent for intent capture, problem framing, idea critique, method design, mathematical explanation, and non-executable design scaffolds. Switch into it (Tab) for the develop stage.
- `labflow-plan` is the primary read-only structured planning agent. It adapts
  Codex Plan Mode semantics to OpenCode tools and emits a final
  `<proposed_plan>` block.
- Switch back to **build** for implementation, **labflow-plan** for structured
  planning, or **labflow-develop** for nonlinear R&D/scaffold work.
- Same-session history carries the research problem anchor, so there is no research-state `UserPromptSubmit` equivalent. A build-only per-turn marker disambiguates the current agent if a prior primary-agent mode prompt lingers after an in-session switch.
- No state-persistence plugin: cross-session recall is left to the user.

## De-Codex mapping

When adapting a shared skill from `plugins/labflow/skills/` into
`opencode/skills/`, rewrite these Codex-isms:

| Codex | OpenCode |
|---|---|
| `$labflow:stage-*` entry | switch primary agent (Tab) |
| `stage-control pass` | no port; continue or choose an explicit agent handoff |
| `request_user_input` | `question` tool |
| `lab-explore` / `lab-research` subagents | built-in `explore` / `scout` subagents |
| stage state under `.codex/labflow-stage/` | none (agent + conversation) |
| reload codex plugin | restart opencode; rerun `install.sh` only for registration/dependencies |
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

5. Rerun `opencode/install.sh` only when plugin registration, package dependencies, or installer behavior changed. Agent, skill, and rule source is read directly from this repo through the `file://` plugin.
6. **Restart opencode** — running sessions keep the already-loaded config.

## OpenCode-specific anti-patterns

- Writing labflow rules into the user's `~/.config/opencode/AGENTS.md` (it
  shadows `~/.claude/CLAUDE.md`); use the additive `instructions` field instead.
- Re-creating a HUD or injecting research state per prompt; the agent name and the narrow build-mode marker already disambiguate the active stage.
- Forcing a state-persistence plugin via compaction hooks unless a proven need
  appears.
- Leaving Codex-isms (`$labflow:`, `request_user_input`, `.codex/`) in adapted
  skill copies.
