# labflow — Codex Plugin Development Context

This file is for agents working on **labflow itself**. It is not shipped into downstream research projects as their project instructions.

## What This Is

**labflow** is a Codex-native research coding skill toolbox.

The current `main` branch is **skill-first**:

- Skills are the primary user-facing interface.
- Prompts are optional manual reference material.
- Background agents are read-heavy helpers for delegation, not top-level personas.
- Obsidian is available as a CLI-backed note system, but labflow no longer tries to enforce an automatic scientific knowledge graph.

Legacy GitHub Copilot support is preserved on the `copilot-legacy` branch. Do not reintroduce Copilot-only structures on `main`.

## Repository Shape

```text
labflow/
├── .agents/plugins/marketplace.json        # Local Codex marketplace entry
├── plugins/labflow/
│   ├── .codex-plugin/plugin.json           # Codex plugin manifest
│   ├── .mcp.json                           # MCP: pdf-reader, augmentcode
│   ├── agents/
│   │   ├── lab-explore.md                  # Read-heavy local code exploration subagent
│   │   └── lab-research.md                 # Read-heavy external research subagent
│   ├── prompts/
│   │   ├── lab.md                          # Optional manual reference prompt
│   │   └── labprompt.md                    # Optional legacy/manual reference prompt
│   ├── hooks/
│   │   ├── hooks.json                       # Plugin-bundled Codex lifecycle hooks
│   │   ├── stage_hook.py                    # Lightweight stage state/context runtime
│   │   └── stage_hud.py                     # Optional tmux HUD for active stages
│   └── skills/
│       ├── annotation/
│       ├── codebase-research/
│       ├── design-scaffold/
│       ├── external-research/
│       ├── git-task-flow/
│       ├── obsidian-cli/
│       ├── pdf-read/
│       ├── self-update/
│       ├── stage-control/
│       ├── stage-goal-clarify/
│       └── stage-idea-refine/
└── README.md
```

There should be no `plugins/labflow/scripts/` launch workflow on `main`.

## Core Design Principles

### 1. Skills Are The Primary Interface

labflow should package stable repeated work as Codex skills.

Current skill boundaries:

- `codebase-research`: local repository investigation; uses augmentcode, `rg`, key-file reads, and `lab-explore` delegation.
- `external-research`: lightweight orchestration for official docs, third-party APIs, upstream source, papers, version differences, GitHub issues/PRs; uses ctx7 CLI first, `gh`/web/pdf-reader as needed, and `lab-research` for high-noise external research.
- `design-scaffold`: design-stage idea concretization; writes distributed prompt material into code skeletons, field docs, TODO anchors, or design notes.
- `git-task-flow`: task-scoped git boundaries, commits, history review, and final push/cleanup mechanics.
- `annotation`: research-oriented code comments and docstrings.
- `obsidian-cli`: Obsidian CLI command reference and safety rules.
- `pdf-read`: PDF/paper reading workflow.
- `self-update`: updating labflow itself.
- `stage-control`: lightweight stage runtime control, state inspection, and hook enablement guidance.
- `stage-idea-refine`: discussion-stage research idea refinement; not a planning or implementation wrapper.
- `stage-goal-clarify`: goal, scope, non-goal, and acceptance-criteria clarification; not a planning or implementation wrapper.

Do not create skills for imagined workflows that have not been proven through repeated use.

Stage skills are the exception only because they are intentionally thin wrappers over a plugin hook runtime. Do not add `stage-plan` or `stage-implement`; Codex native Plan Mode and normal implementation are sufficient.

### Stage Runtime Is Lightweight

The stage runtime exists to keep nonlinear research conversations aligned without recreating OMX-style orchestration.

- Authoritative stage state lives in the active project at `.codex/labflow-stage/state.json`.
- `UserPromptSubmit` may inject current-stage context.
- `Stop` may clear state when the assistant emits a standalone `$stage-pass` / `$stage-cancel`, but must not auto-continue by default.
- Plugin-bundled hooks require `[features].plugin_hooks = true` in Codex config.
- Hook scripts must remain Python standard-library only unless the user explicitly accepts a dependency.
- Do not use non-Codex frontmatter such as `argument-hint`; describe usage in the skill body instead.

### 2. Prompts Are Reference Material, Not Product Surface

`prompts/lab.md` and `prompts/labprompt.md` can remain as manual prompt references, but do not design the plugin around top-level agent switching.

Codex currently does not provide a VS Code top-level custom agent switcher equivalent to `agent.md`. Do not pretend prompts are first-class top-level agents.

### 3. Background Agents Are Read-Heavy Helpers

`lab-explore` and `lab-research` are kept because they can save main-session context during heavy investigation.

- Use `lab-explore` for local codebase exploration.
- Use `lab-research` for external evidence gathering.
- Do not turn them into the main product interface.
- Do not merge their full behavior into a single persona prompt.

### 4. Obsidian Is A Tool, Not An Automatic Research OS

Obsidian remains useful for user-maintained research notes and explicit engineering handoff.

Rules:

- Do not restore `obsidian-research` or automatic `ideas/h/q/f/d` graph maintenance unless the user explicitly asks.
- Do not make agents silently write scientific context or decisions to the vault.
- `engineering-handoff` may write only when the user explicitly provides the target path.
- Before Obsidian writes, verify the active vault with `obsidian vault info=name` and `obsidian vault info=path`.
- Prefer `path=` over `file=` for agent writes.

### 5. Keep Tools Codex-Native

- Use Codex plugin manifest format: `plugins/labflow/.codex-plugin/plugin.json`.
- Use Codex marketplace format: `.agents/plugins/marketplace.json`.
- Use plugin MCP config: `plugins/labflow/.mcp.json`.
- Use plugin hook config at `plugins/labflow/hooks/hooks.json`; do not require project-local hook installation for Labflow stage runtime.
- Avoid Copilot-only assumptions such as `copilot plugin install`, `ask_user`, `.agent.md` top-level launch agents, Copilot `inputs`, or Copilot `tools:` frontmatter.

### 6. Selective Tooling

Prefer the cheapest reliable tool:

- augmentcode for semantic local codebase retrieval when available.
- `rg` for exact local search.
- ctx7 CLI / find-docs for official/version-specific API documentation when available.
- `gh` for GitHub release/source/issue/PR investigation.
- pdf-reader for richer PDF workflows, paper reading, images, and remote PDFs.
- Obsidian CLI for explicit note read/write operations.

## Iterating On labflow

1. Work on `/home/hac/labflow` on the `main` branch.
2. Prefer edits under `plugins/labflow/` unless updating repository-level instructions, README, or marketplace metadata.
3. Validate JSON manifests after manifest changes.
4. Validate skills with `quick_validate.py` after skill changes.
5. Re-add the local marketplace if needed:

```bash
codex plugin marketplace remove riemac
codex plugin marketplace add /home/hac/labflow
```

Changes affect new Codex sessions after the plugin/marketplace is reloaded.

## Anti-Patterns

- Reintroducing `obsidian-research` as a scientific knowledge graph skill.
- Making LabPrompt the central workflow again.
- Reintroducing deleted `codex-lab` / `codex-labprompt` launcher scripts.
- Treating prompts as top-level custom agents.
- Re-adding broad handoff or pseudocode skills without repeated usage evidence.
- Adding broad persona behavior to `AGENTS.md`; this file is for labflow repository rules.
- Turning stage runtime into a heavy planner/executor or adding automatic Stop continuation by default.
- Forcing model overrides in prompts or subagents unless the user explicitly asks.
