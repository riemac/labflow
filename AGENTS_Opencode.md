# labflow — OpenCode Integration Development

Platform-specific guidance for editing the **OpenCode** integration.
Cross-platform conventions (skill-first, bilingual, ability vs stage, tooling,
git hygiene) live in the thin entry [AGENTS.md](AGENTS.md); read that first.

## Product shape

The integration is centered on a single **opencode plugin** loaded via `file://` URL from the repo. The plugin's `config` hook injects rules, agents, and skill paths; the same plugin also registers labflow custom tools.

OpenCode surfaces (all under `opencode/`):

```text
opencode/
├── plugins/
│   └── labflow.ts            # plugin entry: injects rules/agents/skills/tools
├── scripts/
│   ├── config.mjs            # tracked YAML loader, SOPS store, secure provider fetch
│   ├── config-manager.mjs    # bootstrap, migration, age authorization, doctor
│   └── imagegen.mjs          # profiled OpenAI-compatible generation/editing CLI
├── config/                   # tracked defaults, providers, plugins, imagegen routes, SOPS ciphertext
├── package.json              # plugin runtime dependencies such as @opencode-ai/plugin
├── labflow-rules.md          # global cross-agent rules
├── tests/                    # config, migration, security, CLI, and plugin integration tests
├── agents/
│   ├── labflow-develop.md    # primary develop stage: research dialogue + scaffold
│   ├── labflow-plan.md       # primary read-only structured planning stage
│   ├── labflow-paper.md      # primary paper preparation and evidence alignment
│   ├── explore-worker.md     # hidden read-only local/external exploration worker
│   ├── literature-worker.md  # hidden prior-art evidence worker
│   └── learning-worker.md    # hidden learning-system causal evidence worker
├── skills/                   # adapted ability skills (de-Codex'd copies)
└── install.sh                # bootstrap registration and explicit encrypted migration entry point
```

The plugin appears in the opencode Plugin panel and can be toggled
with space (enable/disable) — no need to edit config files after setup.

`labflow-rules.md` carries the persona, feedback-and-discussion, and
distributed-prompting rules; it applies to every agent (build, plan,
labflow-develop, labflow-plan) because the plugin pushes it into
`cfg.instructions`, which is additive and never shadows the user's own
`AGENTS.md` or `~/.claude/CLAUDE.md`.

`imagegen` is a custom tool registered by the plugin and normally reached via the bundled `imagegen` skill. The tool calls `opencode/scripts/imagegen.mjs`, reads named profiles and ordered fallback routes from `opencode/config/imagegen.yaml`, and retains user-supplied legacy JSON, CLI flags, and `OPENCODE_IMAGEGEN_*` as compatibility/override surfaces. The bundled `openai-pro-first` default route receives the current ChatGPT OAuth credential through OpenCode's auth-loader hook and calls the Codex hosted `image_generation` tool directly, then falls back to Lucoo and GMN only for definitive retryable failures; `relay-first` is the one-line configuration alternative. Responses and Codex profiles accept up to four PNG/JPEG/WebP workspace paths through `inputImages`, current-message uploads through `useAttachedImages`, or the session's most recent image-bearing user message through explicit `useLatestAttachedImages`; current/latest scopes are mutually exclusive and one-shot. Reference images make the request an edit, while omitted references preserve fresh text-only generation.

Portable OpenCode defaults and providers live under `opencode/config/`. Provider authentication metadata names aliases in SOPS-encrypted `secrets.sops.yaml`; the plugin decrypts lazily and injects authentication through an in-memory custom `fetch`, so plaintext does not enter the resolved OpenCode config or `opencode debug config`. The generated global config is only a thin machine-local bootstrap for the clone's absolute `file://` plugin URL and third-party startup plugins. Each device has its own untracked age identity; only public recipients and ciphertext are committed.
The old `/imagegen` slash command is intentionally not installed; `install.sh`
only removes the legacy symlink when it points back into this repo.

`literature-forensics` is an OpenCode-only ability skill backed by a local Python
CLI and the hidden `literature-worker` subagent. The primary agent remains the
research lead; workers own bounded topic artifacts, while the primary persists
resumable task IDs in each project's ignored dossier state.

`learning-forensics` is a cross-platform ability backed by the hidden `learning-worker`. Consulting the skill may remain a direct primary-led diagnosis; formal activation builds and seals a fact-only case, launches a comprehensive maximum-useful-parallel blind round, then dynamically narrows to one to three focused lanes, primary-led probes, or re-expansion as evidence changes. The same dossier survives ordinary checkpoint, metric, hypothesis, and causal-focus drift; new dossier roots require a materially different learning object or decision. Workers support blind audit, cross-examination, and exceptional bounded short probes, while primary-owned PTY execution remains the default.

The tracked `opencode-pty` startup plugin provides optional PTY sessions for formal training, live services, and other long-running commands. Global rules assign each long job to one primary-owned session with completion notifications; ordinary background workers continue to use bounded shell commands.

`autopilot` is an OpenCode-only, explicitly activated long-horizon ability. It establishes or maintains one persistent Goal, executes adaptively through native TODO, PTY, child-session, Git, and artifact state, and selects one Research, Coding, or Paper evidence profile. It creates no fixed dossier or workflow log and updates project documentation only when the task, project instructions, or user requires it. The visible upstream `goal` primary agent is disabled, while `/goal` keeps its `agent` unset so Build, Develop, and Paper retain the selected primary agent.

General read-heavy or retrieval-heavy delegation uses the hidden `explore-worker` with explicit `fast`, `normal`, or `deep` scope profiles; `normal` is the default. The worker is read-only, cannot delegate, and covers both local and external evidence. Its prompt and permissions live in `agents/explore-worker.md`; the portable default model and reasoning options live in `config/defaults.yaml`, where built-in `explore` and `general` are disabled. The plugin merges user agent config last so users may replace the provider/model/options without forking the worker behavior.

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
- Same-session history carries the research problem anchor, so there is no research-state `UserPromptSubmit` equivalent. OpenCode's native agent selection and resolved prompt remain authoritative; no per-turn mode prompt is injected. If history confuses build, explicitly restate the implementation intent or start a fresh session.
- No state-persistence plugin: cross-session recall is left to the user.

## De-Codex mapping

When adapting a shared skill from `plugins/labflow/skills/` into
`opencode/skills/`, rewrite these Codex-isms:

| Codex | OpenCode |
|---|---|
| `$labflow:stage-*` entry | switch primary agent (Tab) |
| `stage-control pass` | no port; continue or choose an explicit agent handoff |
| `request_user_input` | `question` tool |
| `lab-explore` / `lab-research` subagents | unified `explore-worker` subagent |
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

1. Work on `/home/hac/labflow`.
2. Edit under `opencode/`. Shared skill source lives in
   `plugins/labflow/skills/`; the OpenCode integration uses adapted copies in
   `opencode/skills/` — keep the de-Codex mapping applied.
3. Validate changed skills:

```bash
python3 /home/hac/.codex/skills/.system/skill-creator/scripts/quick_validate.py opencode/skills/<skill-name>
```

When changing `imagegen` or its plugin bridge, also run:

```bash
(cd opencode && npm test)
```

The imagegen plugin tests import the TypeScript plugin directly and therefore require Node.js 22.6 or newer, as declared in `opencode/package.json`.

4. If `opencode.json` changed (e.g. `mcp`), validate it:

```bash
python3 -m json.tool ~/.config/opencode/opencode.json >/dev/null
```

5. Rerun `opencode/install.sh` only when plugin registration, package dependencies, bootstrap declarations, or installer behavior changed. Use `--init-age` once per device, `--migrate-config` only for explicit global-config migration, `--authorize-age-recipient age1...` from an existing device, and `--doctor` after encrypted configuration changes. The installer reports missing SOPS/age commands but never installs system packages itself.
6. **Restart opencode** — running sessions keep the already-loaded config.

## OpenCode-specific anti-patterns

- Writing labflow rules into the user's `~/.config/opencode/AGENTS.md` (it
  shadows `~/.claude/CLAUDE.md`); use the additive `instructions` field instead.
- Re-creating a HUD or injecting research or agent-mode state per prompt; rely on the visible agent name and native resolved prompt.
- Forcing a state-persistence plugin via compaction hooks unless a proven need
  appears.
- Leaving Codex-isms (`$labflow:`, `request_user_input`, `.codex/`) in adapted
  skill copies.
