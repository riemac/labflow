# labflow — Codex Plugin Development Context

This file is for agents working on **labflow itself**. It is not shipped into downstream research projects as their project instructions.

## What This Is

**labflow** is now a Codex-native plugin for scientific research workflows. It packages reusable skills, MCP configuration, top-level launch prompts, and background research/exploration agents around Obsidian as the persistent knowledge hub.

Legacy GitHub Copilot support is preserved on the `copilot-legacy` branch. The `main` branch is for Codex-only iteration.

## Repository Shape

```text
labflow/
├── .agents/plugins/marketplace.json        # Local Codex marketplace entry
├── plugins/labflow/
│   ├── .codex-plugin/plugin.json           # Codex plugin manifest
│   ├── .mcp.json                           # MCP: pdf-reader, augmentcode, context7
│   ├── agents/
│   │   ├── lab-explore.md                  # Background local code exploration agent
│   │   └── lab-research.md                 # Background external research agent
│   ├── prompts/
│   │   ├── lab.md                          # Top-level Lab session prompt
│   │   └── labprompt.md                    # Top-level LabPrompt session prompt
│   ├── scripts/
│   │   ├── codex-lab                       # Launch Codex with Lab prompt
│   │   └── codex-labprompt                 # Launch Codex with LabPrompt prompt
│   └── skills/
│       ├── annotation/
│       ├── pseudocode/
│       ├── pdf-read/
│       ├── obsidian-cli/
│       ├── obsidian-research/
│       ├── lab-handoff/
│       └── self-update/
└── README.md
```

## Core Design Principles

### 1. Obsidian Vault Is the Only Persistent Research Memory

All cross-session research memory lives in the Obsidian vault. Do not add private `/memories/`, hidden session-state files, or parallel long-term state stores.

Vault structure:

```text
vault root/
├── _context.md            # Research context snapshot, overwritten each handoff, short
├── _progress.md           # Engineering handoff snapshot, overwritten each handoff, no fixed length
├── _progress-history.md   # Changelog, append only, not read automatically at startup
├── ideas/
│   ├── _map.md
│   ├── h-*.md
│   ├── q-*.md
│   ├── f-*.md
│   └── d-*.md
└── tasks/
    └── task-*.md          # LabPrompt writes these; humans choose when to use them
```

Key distinction:

- `_context.md` is scientific context: current hypotheses, directions, decisions, and unresolved questions.
- `_progress.md` is engineering handoff: current target, file/function-level progress, resume guide, and known blockers.
- `tasks/` is a human navigation layer; Lab does not automatically read it.

### 2. Do Not Replace Codex-Native Planning

The vault is human-readable project state. It is not a replacement for Codex's current-session plan/tooling.

- Codex plan/checklist tools are for the current execution session.
- `_progress.md` is for cross-session handoff.
- `tasks/task-*.md` files are prompt briefs that a human can choose to paste or run later.

### 3. Separate Top-Level Workflows From Background Agents

- **Lab** is a top-level Codex session prompt for research discussion and implementation.
- **LabPrompt** is a separate top-level Codex session prompt for discussing vague ideas and forging natural-language execution prompts.
- **lab-explore** and **lab-research** are background agents for bounded delegated investigations.

Do not turn LabPrompt into a background subagent. Its intended UX is a separate Codex window/session.

### 4. Keep Tools Codex-Native

- Use Codex plugin manifest format: `plugins/labflow/.codex-plugin/plugin.json`.
- Use Codex marketplace format: `.agents/plugins/marketplace.json`.
- Use plugin MCP config: `plugins/labflow/.mcp.json`.
- Avoid Copilot-only assumptions such as `copilot plugin install`, `ask_user`, `.agent.md` top-level launch agents, or Copilot `inputs`.

### 5. Selective De-MCP

Prefer CLI tools when they are cheaper and clearer:

- Obsidian CLI for vault read/write.
- `pdftotext` for fast PDF text extraction.
- MCP pdf-reader only for capabilities CLI cannot replace, such as image extraction or remote PDFs.
- augmentcode/context7 MCP when semantic code search or official documentation lookup is materially useful.

## Iterating On labflow

1. Work on the Codex worktree, usually `/home/hac/labflow-codex`.
2. Edit files under `plugins/labflow/`.
3. Validate JSON manifests and scripts.
4. Commit with conventional commits.
5. Re-add or upgrade the local marketplace if needed:

```bash
codex plugin marketplace add /home/hac/labflow-codex
```

Changes affect new Codex sessions after the plugin/marketplace is reloaded.

## Anti-Patterns

- Appending to `_context.md` or `_progress.md` instead of overwriting snapshots.
- Making `_progress.md` replace Codex's current-session plan.
- Making Lab read `tasks/` automatically.
- Reintroducing Copilot-specific agent frontmatter or install instructions on `main`.
- Forcing model overrides in prompts unless the user explicitly asks for that behavior.
