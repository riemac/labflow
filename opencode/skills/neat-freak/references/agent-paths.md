# Agent config & AGENTS.md path cheat-sheet

Codex and OpenCode both use `AGENTS.md` as the primary agent instruction layer,
at the project root and nested in subdirectories. Neither has a separate
"memory file + index" system — everything cross-session lives in `AGENTS.md`.
During Step 1 inventory, enumerate by platform below.

## OpenAI Codex

| Purpose | Path |
|---|---|
| Global instructions | `~/.codex/AGENTS.md` or `$CODEX_HOME/AGENTS.md` |
| Project instructions | project-root `AGENTS.md` (nested allowed) |
| Per-dir override | `AGENTS.override.md` (overrides the sibling `AGENTS.md`) |
| Skills | `~/.codex/skills/<name>/SKILL.md` or project `.codex/skills/<name>/` |

Codex composes instructions from the workspace root down to the edited file's
directory; the most local file wins. Also look for `TEAM_GUIDE.md` / `.agents.md`
as fallback names.

## OpenCode

| Purpose | Path |
|---|---|
| Global config | `~/.config/opencode/` |
| Global instructions | `~/.config/opencode/AGENTS.md` (falls back to `~/.claude/CLAUDE.md`) |
| Project instructions | project-root `AGENTS.md` (nested allowed; `CLAUDE.md` fallback) |
| Extra instruction files | `instructions` array in `opencode.json` |
| Skills (project) | `.opencode/skills/`, `.claude/skills/`, `.codex/skills/` are all scanned |
| Skills (global) | `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.codex/skills/` |

OpenCode walks up from the cwd to the worktree root collecting `AGENTS.md`, then
merges the global file and any `instructions` entries. It reads both Claude Code
and Codex skill directories, so a skill installed under `~/.codex/skills/` is
visible to both Codex and OpenCode.

## Nested AGENTS.md hygiene (the core of this skill)

Because both platforms honor nested files, each `AGENTS.md` rots independently.

- Root `AGENTS.md`: project-wide conventions, red lines, command cheat-sheets,
  the "deeper docs" pointer table.
- Nested `AGENTS.md`: rules specific to that subtree only. Do not duplicate
  project-wide rules into every child — that is the nested-file bloat pattern.
- When trimming, check each nested file against its subtree: does the code it
  describes still exist? Does it contradict the root? Stale or contradictory
  → fix or delete; genuinely-conflicting-but-both-valid → surface to user.

## No separate memory system

Codex and OpenCode have no memory-file layer. Skip "memory" entirely and spend
the effort on:
- project `AGENTS.md` (root + nested)
- `README.md`
- `docs/`

`docs/` and `README` are platform-neutral; you never need two copies.
