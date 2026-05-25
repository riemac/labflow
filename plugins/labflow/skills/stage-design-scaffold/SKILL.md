---
name: stage-design-scaffold
description: Enter a lightweight design scaffolding stage for mature ideas that need to be externalized into distributed prompts before implementation. Use when the user wants to write TODOs, docstrings, field documentation, interface skeletons, module notes, or design anchors across code/docs without doing full implementation.
---

# Stage: Design Scaffold

Use this stage when the idea is mature enough to be written into the project, but the goal is still scaffolding rather than full implementation.

## Contract

Stay in design-scaffolding mode until the stage is passed or cancelled.

- Turn agreed design intent into distributed prompt material near the code/docs that will later consume it.
- Inspect local code/docs before asking where something belongs.
- Write TODO blocks, docstrings, field docs, interface shells, module notes, or markdown design notes.
- Preserve research semantics: assumptions, constraints, equations, examples, edge cases, and acceptance signals.
- Do not implement full behavior unless the user explicitly exits the stage or asks to implement.
- Keep the process nonlinear: one stage may scaffold multiple files or surfaces, and may return to earlier surfaces after review.

## State Semantics

`problem_statement` is the shared stage anchor: the current-best statement of the problem or goal the scaffold is meant to preserve. `problem_clarity` is one of:

- `unknown`: the agent cannot yet reliably restate the problem.
- `fuzzy`: the direction exists, but object, boundary, motivation, success signal, or constraints are unstable.
- `framed`: the problem can be clearly restated and the user broadly accepts it.
- `stable`: the problem statement is stable enough to anchor this stage. It is not solved or permanently locked.

Design scaffold should usually externalize a `framed` or `stable` problem plus design intent. If the problem is still `unknown` or `fuzzy`, clarify it before writing many distributed prompts.

`scaffold_readiness` is the compact HUD-facing state:

- `mapping`: identifying design goal, target surfaces, and open questions.
- `scaffolding`: actively writing distributed prompt material.
- `reviewing`: waiting for or incorporating user review of scaffolded surfaces.
- `ready_to_pass`: the scaffold is sufficient to exit this stage.

The stage also tracks a lightweight map:

- `design_goal`: concise design intent being externalized.
- `target_surfaces`: files/modules/classes/configs/docs likely to receive scaffold material.
- `current_surface`: the surface currently being discussed or edited.
- `completed_surfaces`: short list of surfaces already scaffolded.
- `open_questions`: design questions that still need user judgment.

Update state only when this map materially changes, not every turn:

```bash
python3 scripts/update_scaffold_state.py \
  --state-path <state-file-from-hook-context> \
  --problem-statement "Problem or goal this scaffold preserves." \
  --problem-clarity stable \
  --scaffold-readiness scaffolding \
  --design-goal "Concise design goal." \
  --target-surfaces "module.py: Config fields; docs/foo.md: design note" \
  --current-surface "module.py: Config fields" \
  --open-questions "Question that still needs user judgment" \
  --note "Why this changed."
```

To mark a surface done:

```bash
python3 scripts/update_scaffold_state.py \
  --state-path <state-file-from-hook-context> \
  --scaffold-readiness reviewing \
  --add-completed-surface "module.py: Config fields scaffolded" \
  --note "Surface ready for user review."
```

The `scripts/...` paths are skill-relative. Resolve them against this skill directory, not the current shell working directory.

## Scaffolding Style

Good scaffold material should feel like part of the repository, not a pasted chat transcript.

Prefer:

- `r"""..."""` field docs for declarative configs.
- Class/function docstrings for semantic contracts.
- TODO blocks with inputs, outputs, constraints, and acceptance checks.
- Thin interface shells when names and data flow are stable.
- Markdown notes when the design spans multiple files.

Avoid:

- Generic comments that do not constrain implementation.
- Large centralized prompts disconnected from the target code.
- Completing implementation logic just because the scaffold location is open.

## Completion

The stage can end when the distributed prompt material is sufficient for a future implementer to proceed without re-deriving the design intent.

When `scaffold_readiness=ready_to_pass`, prefer asking the user to send `$labflow:stage-control pass`. Emit a standalone `$labflow:stage-control pass` yourself only when the user clearly asked you to exit the stage.

## Abilities

Use other abilities only when they serve the scaffold:

- `codebase-research`: locate target surfaces and analogous patterns.
- `deep-research` / `external-research`: verify external or cross-source facts that affect the scaffold.
- `annotation`: refine comments/docstrings after the design content is clear.
