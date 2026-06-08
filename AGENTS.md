# labflow — Development Context

This file is for agents editing **labflow itself**. It is repository guidance,
not downstream research-project instructions.

**labflow** is a research coding plugin. The primary interface is skills;
agents, rules, hooks, and MCP support those skills. labflow ships for two host
platforms with different runtime models, so platform-specific guidance lives in
two companion files — **read the one matching what you are editing**:

- **[AGENTS_Codex.md](AGENTS_Codex.md)** — editing the Codex plugin: surfaces
  under `plugins/labflow/` (`.codex-plugin/`, `hooks/`, `.mcp.json`, `agents/`,
  `prompts/`, `skills/`), stage runtime, marketplace, plugin reload.
- **[AGENTS_Opencode.md](AGENTS_Opencode.md)** — editing the OpenCode
  integration: surfaces under `opencode/` (rules file, primary agent, skills),
  `install.sh` deployment, plugin system, and the de-Codex mapping.

Most skills under `plugins/labflow/skills/` are shared source; the OpenCode
integration adapts copies into `opencode/skills/`. When a change
touches both platforms, update both companion files.

## Cross-platform conventions

These hold regardless of host platform.

### Skill-first

Package stable repeated work as skills. Keep `SKILL.md` concise and operational;
move heavy formats or examples into `references/`, deterministic helpers into
`scripts/`, and output assets into `assets/`. Do not create new skills from
imagined workflows — add one when the behavior has repeated use and a clear
boundary.

### Bilingual content convention

- `SKILL.md` is the authoritative, English, agent-facing instruction file.
- `SKILL_CN.md`, when present, is Chinese user-facing discussion/review material.
- Prompt templates follow the same convention: English file authoritative,
  `_CN.md` companion for Chinese discussion.
- Keep paired files semantically synchronized, not mechanically translated.
- Bundled skill paths such as `scripts/foo.py` or `references/bar.md` are
  relative to the skill directory, not the shell cwd.

### Ability vs stage

- A **stage** is a lightweight stateful collaboration mode (Codex: hook context
  + optional HUD; OpenCode: a primary agent you switch into).
- An **ability** is an independent skill for a reusable cognitive, research,
  design, or execution action. Abilities imply no fixed pipeline.
- Native planning/implementation modes remain the default; do not wrap them
  unless there is a proven need.

### Tooling choices

Use the cheapest reliable evidence source:

- Local semantic/code-RAG for candidate recall when file locations are unknown;
  keep queries path-scoped and provider-neutral.
- `tree` / `fd` for structure preview and file discovery (depth limits, excludes).
- `rg` for exact local string search.
- ctx7 / `find-docs` for official or version-specific library documentation.
- `gh` for GitHub release/source/issue/PR evidence.
- pdf-reader for papers, PDFs, tables, and PDF images.
- Obsidian CLI only for explicit vault read/write operations.

### Git hygiene

Use `git-task-flow` for meaningful implementation or documentation tasks.

- Check `git status` before staging.
- Do not mix unrelated local edits into a commit.
- Treat user-validated behavior as the boundary for final semantic commits.
- If verification later fails, keep commits as checkpoints and amend/squash only
  after user confirmation.

### Anti-patterns

- Adding broad persona or downstream research-project behavior to this file.
- Treating optional prompts or background agents as the primary product interface.
- Silently writing scientific decisions to Obsidian or other persistent stores.
- Forcing model overrides in prompts or subagents unless the user explicitly asks.
