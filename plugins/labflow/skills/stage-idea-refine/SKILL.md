---
name: stage-idea-refine
description: Enter a lightweight research idea refinement stage for nonlinear R&D discussions before planning or implementation.
---

# Stage: Idea Refine

Use this stage when the user has a rough research idea and wants to clarify intent, feasibility, technical route, assumptions, or method choices before planning or implementation.

## Contract

Stay in discussion mode until the stage is passed or cancelled.

- Clarify research intent before implementation details.
- Separate discoverable facts from human preferences and tradeoffs.
- Inspect local code/docs for discoverable facts before asking the user.
- Challenge assumptions gently: boundary cases, counterexamples, hidden costs, feasibility risks, and evidence needs.
- Do not enter implementation unless the user explicitly exits the stage or asks to implement.
- If the stage was triggered accidentally while discussing files/hooks/commands, explain the misfire and cancel with a standalone `$labflow:stage-control cancel` line.

## State Semantics

`problem_statement` is the shared stage anchor: the current-best statement of what problem, goal, or research question this stage is organized around. `problem_clarity` describes how reliable that anchor is:

- `unknown`: the agent cannot yet reliably restate the problem.
- `fuzzy`: the rough direction exists, but object, boundary, motivation, success signal, or constraints are unstable.
- `framed`: the problem can be clearly restated and the user broadly accepts it, but it may still change after evidence or counterexamples.
- `stable`: the problem statement is stable enough to anchor this stage. It is not solved or permanently locked.

`exit_readiness` is the compact HUD-facing state:

- `vague`: the user is not yet sure what they want or need.
- `not_ready`: the rough goal is visible, but route, feasibility, conflicts, or method are unclear.
- `candidate`: one or more concrete candidate routes exist, but details remain unsettled.
- `ready_to_pass`: a refined route exists and the stage can exit.

`idea_state` is free text describing the current route, understanding, assumptions, or risks around `problem_statement`. It may change non-monotonically; research discussions can become less clear after a useful challenge.

When the discussion state clearly changes, update it with:

```bash
python3 scripts/update_idea_state.py \
  --state-path <state-file-from-hook-context> \
  --problem-statement "Current problem or research question." \
  --problem-clarity framed \
  --exit-readiness candidate \
  --idea-state "Current concise research idea state." \
  --note "Why this changed."
```

Do not update state mechanically every turn. If `problem_statement` is unset or `problem_clarity` is `unknown`/`fuzzy`, prioritize clarifying the problem before over-committing to a technical route.

The `scripts/...` paths are skill-relative. Resolve them against this skill directory, not the current shell working directory.

## Completion and Brief

When `exit_readiness=ready_to_pass`, prefer asking the user to send `$labflow:stage-control pass`. Emit a standalone `$labflow:stage-control pass` yourself only when the user clearly asked you to exit the stage.

After the stage has truly passed, write a short user-facing recall brief when useful:

```bash
cat <<'EOF' | python3 scripts/write_refined_brief.py --state-path <passed-state-file>
# Idea Refine Brief

- Research question:
- Refined route:
- Key assumptions:
- Deferred/excluded:
- Risks and evidence:
- Next step:
EOF
```

The brief is for user recall and manual copy-paste after compaction or a new session. It is not automatically injected into future stages.

## Abilities

Use abilities only when they serve the current idea-refine discussion. They are optional aids, not a required pipeline.

- `research-brainstorm`: use when the idea needs first-principles teardown, candidate method generation, assumptions, counterexamples, failure modes, and minimal validation probes.
- `deep-research`: use when a key feasibility question, technical route, paper/API/codebase fact, or cross-source claim needs evidence-backed investigation before the idea can be refined.
