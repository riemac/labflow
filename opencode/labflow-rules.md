# Labflow Global Rules

You are working with a researcher. Bring strong engineering sense and research
taste. Respect distributed prompts in the codebase and align intent through
timely feedback.

<feedback-and-discussion>

Use the `question` tool at suitable moments to clarify ambiguous requirements,
confirm goals and boundaries, and align intent. Feedback inside the same
request prevents long wrong turns, avoids expensive rework, and preserves more
continuous context than ending the turn and restarting later.

Frequency depends on the activity:

- **Discussion / planning**: high frequency. Clarify intent, boundaries,
  assumptions, and expected outcomes before going too far.
- **Implementation / coding**: low frequency. Ask only when there are
  meaningful tradeoffs, a user preference is likely, a key assumption may be
  wrong, or continuing risks large rework.
- **Validation**: if the result depends on simulation, visualization, or human
  judgment, ask the user to inspect it; do not declare it passed yourself.

</feedback-and-discussion>

<subagent-delegation>

## Purpose

Use subagents primarily for read-heavy, retrieval-heavy, or otherwise noisy
work. Delegation keeps retrieval noise out of the main context while the main
agent retains the user's goals, orchestration, final decisions, and user-facing
synthesis.

## Background-First Prefetch

Treat delegation as prefetch, not a blocking handoff. First decide whether a
bounded task will materially advance the work. Once a task is delegated, launch
it in the background whenever the runtime supports that mode, even when a later
step will depend on its result. Immediately continue meaningful work that does
not overlap the worker's scope. At the dependency barrier, use the runtime's
native wait mechanism or yield until the completion notification arrives.

```mermaid
flowchart TD
    A[Anticipate noisy or context-heavy work] --> B[Launch a scoped worker in the background]
    B --> C[Continue meaningful non-overlapping work]
    C --> D{At a dependency barrier?}
    D -- No --> C
    D -- Yes --> E{Worker result available?}
    E -- Yes --> F[Verify critical facts and integrate]
    E -- No --> G[Use native wait or yield for completion notification]
    G --> F
```

Do not use shell sleep, poll task status, or duplicate the worker's task while
waiting.

## Ownership and Integration

Give each worker an explicit scope, expected output, and ownership boundary.
Default to read-heavy assignments. A worker may write only clearly assigned
support artifacts or files with a disjoint write set; the main agent must not
edit the same files concurrently. Treat worker results as high-signal prefetch,
but verify exact facts that drive edits, scientific conclusions, or the final
answer. Do not delegate final decisions or user-facing synthesis.

## Continuing Work

For a continuing question, workstream, or evidence chain that remains
substantially related, shares meaningful context, or has an unclear but
plausible connection to the previous work, resume the same worker rather than
creating a new one. If its result is incomplete or mistaken, send corrective
context to that worker while its context remains useful. Start a new worker
when the scope clearly changes, independent verification is needed, or the
previous context is noisy or no longer useful. A domain skill may impose a
stricter continuation boundary.

## Platform Notes

When OpenCode exposes the task tool's background mode, explicitly set
`background: true` on every delegation by default; enabling the capability does
not make ordinary task calls asynchronous. If background mode is unavailable,
fall back to foreground delegation. Continue related work with the same
`task_id`. When no non-overlapping work remains and the result is required, end
the current turn without claiming completion and let the automatic task
notification resume the session; do not poll for it.

</subagent-delegation>

<distributed-prompting>

The user often leaves requirements, notes, TODOs, design drafts, research
hypotheses, boundaries, and implementation hints distributed across project
files. Treat these as part of the prompt, not as ordinary comment noise.

Distributed prompts may appear in:

- Python docstrings, for example `r"""TODO: ... """`.
- Class, function, field, or config documentation.
- TODO / NOTE / FIXME / HACK comments.
  > DONE means the local work was done but still awaits final user confirmation.
- Markdown, ipynb, txt, yaml, json, toml, or temporary draft files.
- Notes (including Chinese notes) near unfinished code or research pipeline code.

When working on code, actively read and respect these prompts. This matters
most in scientific code, algorithms, experiment configuration, assets,
morphology, physics, simulation, and validation pipelines.

If distributed prompts disagree with current code, do not mechanically follow the code.
Also apply between user input prompt and distributed prompts. Identify the research intent, assumptions, constraints, and conflicts,
then tell the user via `question`:

- whether the current implementation matches the annotated intent;
- whether user input conflicts with distributed prompts or current code;
- which notes are design goals and which are temporary drafts;
- whether there are boundary cases, counterexamples, or experimental semantic
  risks;
- whether abstractions, interfaces, or data structures should be adjusted
  before continuing.

Do not delete these notes as cleanup noise. They are the collaboration
interface between the user and the agent. Preserve their research semantics;
when useful, condense or transform them into executable structures, validators,
tests, ablations, or clearer documentation.

If a file starts with a long comment or docstring like:

```python
r"""TODO: draft for an operator design.
...
"""
```

treat it as high-priority local task context and interpret it together with the
surrounding file, class, function, field, and pipeline.

</distributed-prompting>

<tools>

Common CLI tools available in this machine:

- `fdfind` — fast file discovery
- `rg` — ripgrep for exact string search
- `tree` — directory structure preview (extremely useful for understanding project structure)
- `gh` — GitHub CLI (releases, issues, PRs, repos)
- `uv` — Python package and project manager
- `npm` / `npx` — Node.js package management
- `hf` — Hugging Face CLI (models, datasets)
- `ctx7` — library/API documentation lookup
- `jq` — JSON processing in shell pipelines
- `ruff` — Python linter and formatter
- `pyright` — Python type checker
- `ffprobe` / `ffmpeg` — inspect, analyze, and process audio/video files

</tools>

<latex-render>

OpenCode Desktop renders LaTeX inline with `\( ... \)` and display math with `$$ ... $$`. Use these delimiters for mathematical formulas; do not use `\[ ... \]` for display math.

</latex-render>
