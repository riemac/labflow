# labflow — Codex Plugin Development

Platform-specific guidance for editing the **Codex** plugin. Cross-platform
conventions (skill-first, bilingual, ability vs stage, tooling, git hygiene)
live in the thin entry [AGENTS.md](AGENTS.md); read that first.

## Product shape

The Codex plugin is a Codex-native research coding plugin. The primary interface
is skills; hooks, MCP, prompts, and background agents support those skills.

Codex surfaces:

```text
labflow/
├── .agents/plugins/marketplace.json
├── plugins/labflow/
│   ├── .codex-plugin/plugin.json
│   ├── .mcp.json
│   ├── agents/                         # read-heavy delegation templates
│   ├── hooks/                          # stage runtime hooks and HUD
│   ├── prompts/                        # optional reference prompts
│   └── skills/                         # primary user-facing interface
└── README.md
```

Main skill families:

- Research stages: `stage-idea-refine`, `stage-goal-clarify`,
  `stage-design-scaffold`, `stage-control`.
- Research abilities: `research-brainstorm`, `deep-research`,
  `codebase-research`, `external-research`, `pdf-read`.
- Design / implementation support: `annotation`, `git-task-flow`,
  `obsidian-cli`, `self-update`, `neat-freak`.

## Stage-Driven Development

SDD means **do the right work for the current stage until that stage is done**.
It is a lightweight collaboration constraint for nonlinear research work: the
user keeps the long-horizon sense of where the project is, while labflow
provides stage state, reminders, and reusable abilities so Codex does not drift
into the wrong kind of work.

On Codex, a stage is backed by hook context and an optional HUD. Abilities may
be used inside stages or in normal Codex mode. Codex native Plan Mode and normal
implementation remain the default for planning/coding.

`plugins/labflow/prompts/stage-AGENTS.md` is the English source for a user's
top-level Codex `AGENTS.md`; `stage-AGENTS_CN.md` is its Chinese companion.

## Stage runtime

The stage runtime should stay small and predictable:

- State is session-scoped under the active project's `.codex/labflow-stage/`.
- Stage state should include a shared problem anchor when runtime state is
  maintained: `problem_statement` is the current-best statement of what
  problem/goal the stage is organized around, and `problem_clarity` is one of
  `unknown`, `fuzzy`, `framed`, or `stable`. `stable` means stable enough for the
  current stage, not solved or permanently locked.
- `UserPromptSubmit` may inject active-stage context for the matching session.
- Keep injected context compact and stage-specific. For example,
  `stage-idea-refine` may remind Codex to prefer short explanations plus
  `request_user_input`, but do not turn that into a universal rule for
  lower-ambiguity stages such as `stage-design-scaffold`.
- Stage entry commands require explicit plugin-prefixed `$labflow:stage-*` skill
  commands.
- `Stop` records heartbeat and clears state only on standalone
  `$labflow:stage-control pass` / `$labflow:stage-control cancel`; it must not
  auto-continue by default.
- Hook scripts should remain Python standard-library only unless the user
  accepts a dependency.
- HUD is best-effort; failure to open or close a HUD must not block Codex.
  Automated tests should set `LABFLOW_STAGE_HUD_DISABLED=1` instead of opening
  windows that need cleanup.

## Updating the Codex plugin

1. Work on `/home/hac/labflow` on `main`.
2. Prefer edits under `plugins/labflow/`; update root docs only when
   repository-level guidance changes.
3. Before editing a project file, inspect applicable `AGENTS.md` /
   `AGENTS.override.md` from the target path upward.
4. Validate changed skills:

```bash
python3 /home/hac/.codex/skills/.system/skill-creator/scripts/quick_validate.py plugins/labflow/skills/<skill-name>
```

5. Validate manifests when changed:

```bash
python3 -m json.tool plugins/labflow/.codex-plugin/plugin.json >/dev/null
python3 -m json.tool plugins/labflow/.mcp.json >/dev/null
python3 -m json.tool plugins/labflow/hooks/hooks.json >/dev/null
python3 -m json.tool .agents/plugins/marketplace.json >/dev/null
```

6. Reload the installed local plugin when runtime behavior, hooks, manifest, or
   skill discovery must be tested from Codex:

```bash
/home/hac/labflow/plugins/labflow/skills/self-update/scripts/reload_labflow_plugin.sh
```

Changes to installed plugin content are fully visible in new Codex sessions
after reload.

## Codex-specific anti-patterns

- Turning stage runtime into a planner/executor or heavy workflow orchestrator.
- Adding automatic Stop continuation by default.
- Reintroducing Copilot-only assumptions on `main`.
