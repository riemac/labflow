---
name: stage-goal-clarify
description: Enter a lightweight goal clarification stage for success criteria, scope, non-goals, and acceptance checks.
---

# Stage: Goal Clarify

Use this stage when the user needs to turn an intent into a concrete goal, boundary, or acceptance contract before planning or implementation.

## Stage Contract

Stay in clarification mode until the stage is passed or cancelled.

- Maintain the shared problem anchor conceptually: `problem_statement` is what problem or goal the clarification is organized around, and `problem_clarity` should move from `unknown`/`fuzzy` toward `framed`/`stable` as the stage succeeds.
- Identify the goal, success criteria, non-goals, and acceptance checks.
- Make hidden constraints explicit: target audience, runtime context, safety limits, validation method, and rollback expectations.
- Use local inspection for facts instead of asking the user for discoverable details.
- Ask focused questions only for high-impact preferences or tradeoffs.
- Keep the output decision-oriented, not bureaucratic.
- Do not enter implementation unless the user explicitly exits the stage or asks to implement.

## Completion

The stage can end when the implementer would not need to make major product or research decisions.

If complete, ask the user to send `$labflow:stage-control pass` or include a standalone `$labflow:stage-control pass` line.
