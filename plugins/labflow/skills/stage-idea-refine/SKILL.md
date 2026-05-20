---
name: stage-idea-refine
description: Enter a lightweight research idea refinement stage for nonlinear R&D discussions before planning or implementation.
---

# Stage: Idea Refine

Use this stage when the user wants to discuss a research idea, technical route, method choice, feasibility risk, or vague design direction before planning or implementation.

## Stage Contract

Stay in discussion mode until the stage is passed or cancelled.

- Clarify the underlying research intent before implementation detail.
- Separate discoverable facts from human preferences and tradeoffs.
- Inspect local code/docs for facts before asking the user about repository internals.
- Challenge assumptions gently: identify boundary conditions, counterexamples, hidden costs, and failure modes.
- Keep the workflow lightweight. Do not produce a full PRD unless the user asks.
- Do not enter implementation unless the user explicitly exits the stage or asks to implement.

## Completion

The stage can end when the research direction is clear enough for the next natural step.

If complete, ask the user to send `$stage-pass` or include a standalone `$stage-pass` line.
