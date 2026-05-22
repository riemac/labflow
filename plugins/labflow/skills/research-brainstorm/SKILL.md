---
name: research-brainstorm
description: Use when a research idea, algorithmic route, representation choice, experiment design, robotics/CV/ML method, or scientific hypothesis needs first-principles ideation before planning or implementation. Use to generate and critique candidate methods, expose assumptions and counterexamples, design minimal validation probes, and compare conservative, ambitious, and wild-but-plausible research routes. Do not use for ordinary product brainstorming or pure implementation planning.
---

# Research Brainstorm

Generate research method candidates from first principles, then critique each one. This is an ability skill, not a stage: use it inside `stage-idea-refine`, `stage-goal-clarify`, or normal Codex mode when the user needs scientific ideation rather than a software plan.

## Contract

- Treat the user as a research partner, not a client receiving a fixed design.
- Start from mechanism: physical geometry, dynamics, statistics, representation, learning signal, optimization pressure, data distribution, or simulator constraints.
- Generate ideas and critique them in the same pass; do not only list possibilities.
- For each serious idea, name assumptions, failure modes, counterexamples, and the smallest experiment that could falsify or support it.
- Use lightweight local/external research when a key fact is discoverable and would change the brainstorm. Do not turn this skill into a broad survey unless the user asks.
- Keep abilities independent: this skill may coexist with codebase research, external research, deep evidence synthesis, or design scaffolding, but it does not imply a fixed pipeline.

## Workflow

1. **Frame the research problem**
   - Restate the core question in one sentence.
   - Identify the object of study, desired capability, metric, controllable variables, constraints, and unknowns.
   - If the user’s preference would substantially change the search space, ask one focused question; otherwise state assumptions and continue.

2. **Tear down the idea**
   - Ask what must be true for the idea to work.
   - Look for hidden coordinate-frame, topology, morphology, data-distribution, simulator, or optimization assumptions.
   - Surface at least one plausible counterexample or degenerate case.

3. **Generate method axes**
   Consider only axes relevant to the problem:
   - representation / tokenization / geometry;
   - model architecture / inductive bias;
   - learning signal / objective / reward;
   - data generation / curriculum / domain randomization;
   - physics / morphology / simulator constraints;
   - validation, ablation, and metrics;
   - integration cost and codebase fit.

4. **Return method cards**
   Use compact cards by default. For a heavier artifact, read `references/method-card.md`.

   ```text
   ### <method name>
   - Core idea:
   - Why it might work:
   - Key assumptions:
   - Failure modes / counterexamples:
   - Minimal validation:
   - Cost / risk / novelty:
   - Fit to current project:
   ```

5. **Converge**
   - Group candidates as `safe`, `promising`, `risky`, and `do-not-do`.
   - Recommend 1-3 next probes, not a full implementation plan unless asked.
   - If the discussion is inside a stage, help the stage move toward its exit criteria; do not auto-pass the stage.

## Output Style

- Prefer short Chinese explanations when the user speaks Chinese.
- Use equations, small tables, or Mermaid only when they clarify the research mechanism.
- Be willing to challenge the premise kindly: “这个假设可能不稳，因为…”.
- Avoid generic advice like “try a transformer/GNN” unless tied to a mechanism and validation probe.
- Avoid claiming novelty without evidence; mark novelty as a hypothesis if not researched.

## Anti-Patterns

- Do not force a brainstorm → research → scaffold sequence.
- Do not produce a PRD, SPEC, or task plan unless the user asks to leave ideation.
- Do not drown the user in a literature survey when the immediate need is idea formation.
- Do not treat software architecture cleanliness as more important than scientific validity.
- Do not hide uncertainty; uncertainty is often the useful output.
