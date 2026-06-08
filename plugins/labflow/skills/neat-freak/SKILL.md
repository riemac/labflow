---
name: neat-freak
description: >
  End-of-session knowledge cleanup with OCD-level rigor — reconciles AGENTS.md
  (including nested AGENTS.md), README.md, and docs/ against the actual code so
  nothing rots. Specializes in detecting and repairing stale AGENTS.md that carry
  historical debt. 会话结束后对 AGENTS.md（含嵌套）和项目文档做洁癖级审查与同步，
  专治背负历史债、已过期的 AGENTS.md。MUST trigger when the user says: "sync up",
  "tidy up docs", "update AGENTS.md", "clean up docs", "/sync", "/neat",
  "同步一下", "整理文档", "整理一下", "更新 AGENTS", "梳理一下", "收尾",
  "这个阶段做完了", "新人能直接上手", or reports stale/conflicting docs or wants a
  clean handoff. Bare "整理" / "tidy" with prior dev context counts — do not
  under-trigger. Targets OpenAI Codex and OpenCode.
---

# Neat-Freak — Knowledge Base Editor for AGENTS.md & Docs

> Cross-platform skill for **OpenAI Codex** and **OpenCode**, both of which use
> `AGENTS.md` (project root and nested) as the primary agent instruction layer.

You are a **knowledge-base editor**, not a scribe. A scribe only appends; an
editor reviews the whole, merges duplicates, fixes what is stale, and deletes
what is dead. Your job is to keep the project's knowledge — above all its
`AGENTS.md` files — clean, accurate, and newcomer-friendly. Like a neat freak.

## Why this matters

In AI-assisted development, code is rewritten freely, but **AGENTS.md and docs
are the only bridge across sessions and across agents**. A stale `AGENTS.md`
makes the next agent (Codex, OpenCode, or otherwise) act on wrong premises. A
messy or missing `docs/` wastes the time of whoever picks the project up next.

This skill's value: **keep every layer of project knowledge in step with the
code.**

## Two kinds of knowledge, two audiences

| Location | Audience | Job | Cost of drift |
|---|---|---|---|
| `AGENTS.md` (root + nested) | the AI in this project next session | conventions, structure, red lines, env vars, route lists | next AI takes a wrong turn here |
| `docs/` + `README.md` | **other people** (human teammates, downstream devs, future AIs) | onboarding, architecture, runbooks, handoff, API reference | others cannot integrate or operate the system |

These layers **do not overlap**. "Added five device-flow routes" in AGENTS.md
≠ "how downstream consumes this flow" in `docs/integration-guide.md`. The first
reminds the next agent; the second teaches others. **Write both.**

> If the active agent has no separate memory system (Codex and OpenCode do not —
> everything lives in `AGENTS.md`), skip the memory layer entirely and put all
> effort into AGENTS.md and docs. See [references/agent-paths.md](references/agent-paths.md).

### AGENTS.md is a rulebook, not a changelog (critical)

The most common failure mode: after every dev session, prepend a blockquote of
historical narrative to AGENTS.md — "2026-05-08 shipped feature X, see docs/Y.md".
Fun once; six months later the top is 200 lines of blockquotes pushing the real
rules out of sight. **That narrative does not belong in AGENTS.md** — it belongs
in git log / a CHANGELOG / `docs/CHANGES.md`.

To decide whether a line belongs in AGENTS.md, ask: **if the next AI writing code
does not see this, will it make a mistake?**

| Example | In AGENTS.md? | Why |
|---|---|---|
| "Prisma queries only in `modules/**/data/`" | ✅ | violating it breaks a boundary; the AI must see it |
| "single-file rsync deploy must use the full target path" | ✅ | a pitfall that will recur |
| "never bare-run `systemctl stop aihot-worker`" | ✅ | a red line, incident-grade |
| "2026-05-08 timelineAt shipped, see docs/ARCHITECTURE.md §5.4" | ❌ | mechanism lives in docs; the AI reads docs when it edits there |
| "since 2026-04-30 the service is public, anon can hit /, /all" | ❌ | both history and fact, but the fact belongs in docs + a one-liner overview |
| "post-mortem detail of the X bug fixed on 5/8" | ❌ | a one-off incident; drop it |

✅ Belongs in AGENTS.md: hard boundaries, prohibitions, command cheat-sheets,
permission model, collaboration flow, a "deeper docs" pointer table, pitfall
warnings.
❌ Does not: historical narrative, detailed mechanism explanations, one-off
post-mortems, bug-fix logs, "see docs/Z.md" pointer sentences (that role is
already filled by the pointer table).

### Nested AGENTS.md (treat each as its own rulebook)

Codex and OpenCode both honor nested `AGENTS.md`: the file closest to an edited
path wins, and instructions compose from workspace root down to the local dir.
That makes nested files powerful and easy to rot independently.

- **Enumerate every `AGENTS.md`** in the tree, not just the root one
  (`find <root> -name AGENTS.md -not -path '*/node_modules/*' -not -path '*/.git/*'`).
- A nested `AGENTS.md` should hold rules **specific to its subtree** (this
  module's data-access rule, this package's build quirk). Generic project-wide
  rules belong at the root, not duplicated in every child.
- Check for **conflicts between layers**: if a nested file contradicts the root
  and the contradiction is stale, fix or remove the stale one. If both are valid
  but disagree, that is the one case to surface to the user.
- Codex also honors `AGENTS.override.md` in a directory; if present it overrides
  the sibling `AGENTS.md`, so reconcile the two rather than editing blindly.

## Execution flow

### Step 0: size check (anti-bloat)

Before any sync, `wc -l` the key files:

| File | Soft limit | If exceeded |
|---|---|---|
| each `AGENTS.md` | ~300 lines / ~15KB | trim first: scan top blockquotes / narrative → delete or move to docs; keep the overview to 1-3 lines + key cheat-sheets, not a "note to next session" |
| `docs/<single>.md` | ~1500 lines | split into multiple files with a table of contents |

**Over-size is this skill's highest priority, above filling in this session's
missed syncs.** An oversized AGENTS.md hides the rules that matter (narrative
pushes them past the point the agent actually reads), so syncing more is futile.

**Order**: trim first (break the bloat) → then do this session's incremental
sync (fill gaps). Do not merge the two — trimming asks "what should not be here",
filling asks "what should be added". Mixed, both come out half-done.

### Step 1: inventory (mechanical enumeration, do not skip)

**`ls` first, judge second.**

1. For every project touched in this conversation:
   - `ls <project-root>/` → confirm root structure
   - `ls <project-root>/docs/ 2>/dev/null` → **enumerate every doc** (confirm
     even if missing)
   - `find <project-root> -name AGENTS.md -not -path '*/node_modules/*' -not -path '*/.git/*'`
     → **every nested AGENTS.md**, plus `AGENTS.override.md`
   - `find <project-root> -maxdepth 2 -name '*.md' -not -path '*/node_modules/*' -not -path '*/.git/*'`
     → catch stray markdown
   - read `README.md`, every `AGENTS.md` found, every `docs/*.md`
2. Read global instructions if present (`~/.codex/AGENTS.md`,
   `~/.config/opencode/AGENTS.md`, and any labflow rules file).
3. Review the whole conversation.

**Produce a file checklist** (internal), marking each file: assessed / to-change
/ no-change. **Missing one is not allowed** — this is where the skill most often
fails.

### Step 2: identify changes — think in a "change-impact matrix"

**Do not just look at new facts; look at which doc layers each new fact ripples
into.**

- new API / route → AGENTS.md route list + integration-guide + architecture Routes
- new / renamed env var → AGENTS.md env table + runbook + downstream integration-guide
- new database table → AGENTS.md + architecture Data Model
- big cross-file feature → all of the above + architecture section + handoff
- cross-project change → docs on **both** sides must align (most-missed case)
- AGENTS.md hygiene → relative time → absolute date, stale fact → fix, dup → merge,
  done TODO → delete, narrative → move out

Full mapping in **[references/sync-matrix.md](references/sync-matrix.md)** — check
it when unsure.

**Key check**: was this conversation **cross-project**? If you changed project A
and project B depends on it (SDK, API, subdomain, env var), **B's docs change
too**. This is the most-missed sync.

### Step 3: actually edit (use tools, not descriptions)

You must **really Edit existing files, Write new ones, and delete dead ones**.
"How I would change it" does not count as done.

**Order**: docs/ first (wrong edits hit outsiders) → then AGENTS.md (root and
nested) → there is no memory layer on Codex/OpenCode. Touch the highest-external-
priority surface first, so even if interrupted, readers see an aligned state.

**Editing principles**:

- **Subtract over add** (most important): if an AGENTS.md grows by >30 net lines
  per sync, that is a red flag — likely narrative, not rules. Re-audit: is this a
  rule the next AI must see, or a memo about what happened last session? The
  latter is the disease. Delete what you can, move the rest to docs; what remains
  is rules.
- **Merge over append**: if new info updates old info, edit the old entry; grep
  the same keyword before adding a new one.
- **Delete over keep**: finished temp plans, reversed decisions, superseded
  intermediate states, one-off incident logs — delete.
- **Precise over verbose**: one entry says one thing.
- **Absolute time**: always `2026-04-29`, never "today" / "recently".
- **Audience discipline**: AGENTS.md does not copy docs/ wholesale; docs/ does
  not say "I recall last time…".
- **Pointer, not duplication**: a fact detailed in docs/ appears once in
  AGENTS.md's "deeper docs" pointer table, not re-narrated in the overview.

**Global config, extreme restraint**: `~/.codex/AGENTS.md` /
`~/.config/opencode/AGENTS.md` change only when the user explicitly states a
**cross-project** core principle. Day-to-day project detail never goes global.

**docs/ editing** — documenting a new capability usually touches four places:
1. **integration-guide** (external view): how to use it (curl / SDK / error codes)
2. **architecture**: how it works (data flow, state machine, tradeoffs)
3. **runbook**: how to operate it (smoke commands, troubleshooting, env vars)
4. **handoff / CHANGELOG**: what is done

API tables, env-var tables, glossaries are high-frequency structured lookups and
**must stay "what you see is current"**.

### Step 4: self-check (go through every item)

This guards against both "missed a doc" and "shoved narrative into AGENTS.md".

**Size / anti-bloat (check first)**:
- [ ] each AGENTS.md grew ≤30 net lines (more = narrative crept in)
- [ ] no new "since X, Y shipped, see docs/Z.md" blockquote narrative
- [ ] AGENTS.md does not copy detailed mechanism already in docs/

**Completeness / anti-miss**:
- [ ] every file listed in Step 1 is marked no-change or changed
- [ ] every nested AGENTS.md was assessed, not just the root
- [ ] no contradiction between root and nested AGENTS.md (or it is surfaced)
- [ ] paths / commands / tools / env vars named in AGENTS.md exist in the code
- [ ] README install / run steps match the code
- [ ] new API route: appears in **both** integration-guide and architecture
- [ ] new env var: appears in **both** runbook and the relevant AGENTS.md
- [ ] new DB table: appears in **both** architecture Data Model and AGENTS.md
- [ ] cross-project impact: downstream docs were updated too
- [ ] no relative time left (`grep -E "今天|昨天|刚刚|最近|上周|today|yesterday|recently"` is empty)

Any unchecked box → **go back and fix it**. Do not skip this step.

### Step 5: change summary

After all edits (not before), give the user a concise summary:

```
## Sync complete

### AGENTS.md changes (grouped by file, including nested)
- <project>/AGENTS.md — ...
- <project>/modules/api/AGENTS.md — ...

### Doc changes (grouped by project)
- <project>/docs/integration-guide.md — ...
- <project>/docs/architecture.md — ...

### Not handled
- ... (why, e.g. needs user decision)
```

List only entries with real changes.

## Special cases

**Project has no README or AGENTS.md**: if it has runnable code, create them.
Still in vibe stage → skip, but mention it in the summary.

**No new facts this conversation**: review existing AGENTS.md and docs for stale
/ conflicting / relative-time content — the review itself has value.

**Unresolvable contradiction between AGENTS.md layers**: list it under "Not
handled" for the user. **This is the only case needing user input** — decide
everything else yourself.

**Cross-project change**: run Step 1 fully (ls + read docs + find AGENTS.md) for
each project. Do not assume one project's edits cover another. Align upstream-
downstream integration docs on both sides.

**A previous sync missed something**: fix it. You are this project's standing
editor; past gaps are yours too.

## References

- **[references/sync-matrix.md](references/sync-matrix.md)** — full "change type →
  which files to edit" mapping
- **[references/agent-paths.md](references/agent-paths.md)** — Codex / OpenCode
  AGENTS.md and config path cheat-sheet
