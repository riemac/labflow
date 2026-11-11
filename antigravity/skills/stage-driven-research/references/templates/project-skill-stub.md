---
name: stage-research
description: "Stage-driven research workflow for this project. Guides experiment recording, run-card logging, and MAP evolution within the Research/ vault according to nested AGENTS.md rules."
---

# Stage Research

Project-specific skill for conducting stage-driven research in this repository.

## Guiding Principles

All experiment tracking, stage creation, run-card writing, and MAP updates are governed by the nested rules in the `Research/` directory:

1. **Top-level vault rules**: [`Research/AGENTS.md`](../../Research/AGENTS.md)
   - Read/write boundaries (personal ideation in `总体/` and `进展/` is read-only).
   - Mathematical formula formatting (`$$\Large ...$$` for display, `$\large ...$` inline).
   - Tone constraints and Codex-specific anti-defensive writing directives.

2. **Stage-level rules**: [`Research/stages/AGENTS.md`](../../Research/stages/AGENTS.md)
   - Sequential run naming (`runs/01-name.md`, `02-name.md`).
   - Run card metadata schema and node promotion criteria (`node_id: Nxxx`).
   - Unified `MAP.md` conventions (Mermaid DAG + node index table).
   - Post-stage retrospectives (`STAGE-REVIEW.md`).

Consult the corresponding `AGENTS.md` before reading or editing research files.
