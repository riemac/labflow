# labflow — AI Coding Agent Context

This file provides context for AI agents working on the **labflow** plugin itself (self-updates, refinements, new features). It is NOT part of the plugin and does NOT affect projects that install labflow.

---

## What This Is

**labflow** is a GitHub Copilot CLI plugin for scientific research workflows. It packages reusable agents, skills, and MCP configuration into an installable plugin that integrates Obsidian as the primary knowledge hub.

**Installs as:** `copilot plugin install ~/labflow`  
**Users:** Researchers working on projects like IsaacLab-based robotics, simulation, reinforcement learning.

---

## Architecture

```
labflow/
├── plugin.json              # Plugin manifest
├── .mcp.json                # MCP: pdf-reader, augmentcode, context7
├── agents/
│   ├── Lab.agent.md         # Main research agent (idea exploration + execution)
│   ├── LabExplore.agent.md  # Subagent: local codebase exploration
│   ├── LabResearch.agent.md # Subagent: external research (no DeepWiki)
│   └── LabPrompt.agent.md   # Pre-work agent: crystallize vague needs into precise prompts
└── skills/
    ├── annotation/          # Scientific code annotation (67%+ comment density, LaTeX)
    ├── pseudocode/          # Skeleton + TODO pseudocode for design phase
    ├── pdf-read/            # Dual-mode: MCP (full features) + pdftotext CLI (fast text)
    ├── obsidian-cli/        # Obsidian CLI tool reference (copied from obsidian-skills plugin)
    ├── obsidian-research/   # Research vault domain knowledge (structure, templates, workflow)
    ├── lab-handoff/         # End-of-session vault refresh (overwrite _context.md, _progress.md)
    └── self-update/         # Procedure for iterating on labflow itself
```

---

## Core Design Principles

### 1. Obsidian Vault as the Only Persistent Memory
All cross-session research memory lives in the Obsidian vault. No `/memories/` private files, no `session-state/memory.md`. The vault is the single source of truth.

**Vault structure:**
```
vault root/
├── _context.md            ← Research context snapshot (OVERWRITE each handoff, ≤1 page)
├── _progress.md           ← Engineering handoff doc (OVERWRITE each handoff, no length limit)
├── _progress-history.md   ← Changelog (APPEND only, agent never reads at startup)
├── ideas/
│   ├── _map.md            ← MOC (idea discussion mode)
│   ├── h-*.md             ← hypothesis atoms
│   ├── q-*.md             ← question atoms
│   ├── f-*.md             ← finding atoms
│   └── d-*.md             ← decision atoms
└── tasks/
    └── task-*.md          ← Task briefs (LabPrompt writes, human navigation layer)
```

**Key distinction:**
- `_context.md` = scientific context (hypotheses, directions, decisions) — always ≤1 page
- `_progress.md` = engineering handoff (current target, progress to file/function level, resume guide) — no length limit, overwritten
- `tasks/` = human navigation layer, agents do NOT read this automatically

### 2. Don't Interfere with Agent-Native Mechanisms
The vault is for **human-readable project state**, not agent-internal execution planning.

- **CLI built-in plan** = agent's internal task steps (current session, engineering-level)
- **`_progress.md`** = cross-session handoff doc (project-level, human-readable)
- **`tasks/task-*.md`** = task briefs crystallized by LabPrompt (human navigation)

Never make the vault replace the CLI's built-in plan/todo/spec mechanism. The vault and the CLI plan operate at different abstraction levels and timescales.

### 3. ideas/ Vault Access is On-Demand, Mode-Independent
Any conversation mode can read ideas/ atoms when the context calls for it. The agent uses `obsidian search` before making decisions that might touch existing hypotheses or findings.

Write rules:
- **Execution mode decisions** → `d-*.md` atom
- **Test/experiment conclusions** → `f-*.md` atom
- Atoms are NEVER deleted — mark as `status: resolved` or `status: abandoned`

### 4. Selective De-MCP
Use CLI tools (obsidian CLI, pdftotext) where possible to minimize context overhead. Keep pdf-reader MCP for features CLI can't replace (image extraction, remote URLs). augmentcode MCP is primary for local code search.

### 5. Agent Separation
- **Lab** = execution-focused (idea discussion + code implementation)
- **LabPrompt** = pre-work, separate session, produces `tasks/task-*.md` artifacts
- **LabExplore / LabResearch** = background subagents, never use `create`/`edit`/`ask_user`

---

## How to Iterate on labflow

1. **Edit** files in `~/labflow/agents/` or `~/labflow/skills/`
2. **Commit** with conventional commits (`refactor:`, `feat:`, `fix:`)
3. **Reload cache:** `copilot plugin install ~/labflow`
4. **Changes take effect in the NEXT session** (current session uses cached content)

Use the `self-update` skill for the full guided procedure.

---

## Key Technical Facts (First-Hand Verified)

- `tools: [...]` in agent frontmatter = **whitelist filter**, not additive. Omit it to inherit all tools.
- `agents: [...]` = VS Code only, causes warnings in CLI. Don't write for CLI agents.
- `model:` in frontmatter = optional override. User selects model at invocation time.
- Plugin installs are **global** (`~/.copilot/installed-plugins/`). No native project-scoping.
- Project-level overrides: place agents/skills in `.copilot/agents/` or `.copilot/skills/` within the project directory.
- Background subagents cannot respond to permission dialogs. Don't use `create`/`edit`/`ask_user` in subagents.
- Plugin cache must be refreshed after changes: `copilot plugin install ~/labflow`

---

## Anti-Patterns to Avoid

- ❌ Appending to `_context.md` instead of overwriting — it becomes a historical log
- ❌ Making `_progress.md` replace the CLI plan — they're at different abstraction levels
- ❌ Making Lab read `tasks/` automatically — it's a human navigation layer
- ❌ Adding `tools: [...]` to agent frontmatter — restricts rather than extends
- ❌ Big-bang refactors — change one clear thing at a time, verify next session
