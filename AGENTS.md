# labflow — Development Context

This file is for agents editing **labflow itself**. It is repository guidance,
not downstream research-project instructions.

**labflow** is a personal research workflow toolbox. The primary interface is skills;
agents, rules, and MCP support those skills. labflow ships across three peer
platforms with distinct runtime models, while model channels and credentials live
in a shared Single Source of Truth:

- **`provider/`** — [provider/README.md](provider/README.md): Single Source of Truth for model channels, endpoints, limits, capabilities, and SOPS-encrypted secrets.
- **`codex/`** — **[codex/AGENTS.md](codex/AGENTS.md)**: editing the Codex plugin (`.codex-plugin/`, `.mcp.json`, `agents/`, `skills/`), marketplace, plugin reload, and dedicated research workers.
- **`opencode/`** — **[opencode/AGENTS.md](opencode/AGENTS.md)**: editing the OpenCode integration (`plugins/`, primary agents, stages, rules, skills), `install.sh` deployment, and provider resolution.
- **`copilot/`** — **[copilot/AGENTS.md](copilot/AGENTS.md)**: editing the Copilot integration (`plugin.json`, `mcp.json`, `com.github.copilot/`), Agents Window orchestration, and provider sync.

The platforms share research contracts where useful, but do not require a symmetric skill catalog. Codex uses a native primary agent for research evidence and document work with native GPT models; OpenCode maintains coding agents; Copilot leverages the VS Code Agents Window and CLI. Keep literature/learning dossier formats and portable helpers compatible, and adapt only host orchestration. When a change touches multiple platforms, update their corresponding companion files.

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

### Markdown source style

- Write each complete prose paragraph as one physical line in Markdown files; let Obsidian, VS Code, and renderers handle visual wrapping.
- Do not hard-wrap prose to a fixed column width. Keep deliberate line breaks for headings, paragraph boundaries, lists, blockquotes, tables, code fences, formulas, frontmatter, and XML-style semantic containers.

### Ability vs stage

- A **stage** is a lightweight collaboration mode. OpenCode represents it with a primary agent; Codex uses its native primary agent and Plan Mode without a Labflow stage runtime; Copilot utilizes the Agents Window and session handoffs.
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
