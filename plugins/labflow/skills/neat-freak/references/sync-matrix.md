# Change-impact matrix

Check this when unsure which files a change should sync. **Both directions**:
fill gaps (add to which files) + anti-bloat (delete from which files).

## Reverse: what to DELETE from AGENTS.md

AGENTS.md is not a changelog. Found these anti-patterns → delete / move:

| Anti-pattern | Action |
|---|---|
| "since X, feature Y shipped, see docs/Z.md" blockquote | delete — the pointer role is filled by the "deeper docs" table; narrative goes to git log / CHANGELOG / `docs/CHANGES.md` |
| copying docs/ mechanism / data flow / scoring formula into AGENTS.md | delete — the AI reads docs when it edits there; AGENTS.md keeps only boundary rules |
| "new feature shipped" narrative stable ≥7 days | fold the durable fact into the overview; delete pure history |
| one-off incident post-mortem ("X went down 30min because Z") | keep a 1-line red line ("don't bare-run systemctl stop X"); detail goes to docs/PLAYBOOK.md or is deleted |
| superseded intermediate state ("5/6 changed X, 5/8 changed to Y") | keep only the final-state rule; delete the middle history |
| a nested AGENTS.md duplicating a project-wide root rule | delete from the child; keep it only at the root |
| a nested AGENTS.md describing code that no longer exists in its subtree | delete or rewrite to match the current code |

Test: **if the next AI does not see this line while writing code, will it err?**
No → delete / move.

## Code change → doc change

| What happened in this conversation | Files to edit (by audience) |
|---|---|
| new API / route | AGENTS.md route list · `docs/integration-guide.md` API table · `docs/architecture.md` Routes |
| new / renamed env var | AGENTS.md env table · `docs/operator-runbook.md` env section · `docs/integration-guide.md` (if downstream configures it) |
| new DB table / column | AGENTS.md data section · `docs/architecture.md` Data Model |
| new / changed user flow | AGENTS.md user flow · README CLI examples · `docs/handoff.md` What Exists Today |
| big feature (cross-file) | all of the above + `docs/architecture.md` new section + `docs/handoff.md` done list |
| new term / renamed concept | `docs/integration-guide.md` glossary + global search-replace old term |
| deploy params / infra change | `docs/operator-runbook.md` · AGENTS.md deploy section |
| downstream integration change | downstream `docs/<integration>.md` · upstream `integration-guide.md` |
| subtree-specific rule (e.g. this module's data-access boundary) | the **nested** AGENTS.md for that subtree, not the root |

## Cross-project impact check

Most-missed scenarios:

- **upstream API changed → downstream SDK docs**: protocol change must align both sides
- **shared subdomain / route / env var changed → every consumer project's setup docs**
- **auth platform change → every integrating app's integration guide**
- **shared component / infra upgrade → version mentions in each project's runbook**

How to judge: did this change touch an SDK, subdomain, shared config, or
cross-process protocol? If so, grep every dependent project's docs for mentions.

## Doc structure convention

Documenting a new capability (API, flow, feature) — the standard move is **four
places**:

1. **integration-guide / external view**: how to use (curl / SDK / error codes)
2. **architecture**: how it works (data flow, state machine, tradeoffs)
3. **runbook**: how to operate (smoke commands, troubleshooting, env vars)
4. **handoff / CHANGELOG**: what is done

API tables, env-var tables, glossaries are high-frequency structured lookups and
**must stay "what you see is current"**.
