---
name: autopilot
description: "Use ONLY when the user explicitly asks to start autopilot, auto, autoresearch, unattended work, overnight work, or a long autonomous iteration. Establish one high-level execution contract, then autonomously research, implement, run bounded experiments, analyze evidence, update the agreed artifacts, and iterate without further questions until success, interruption, the time budget, or a hard blocker. OpenCode-only: use background subagent notifications and PTY exit notifications for event-driven continuation; a user-started Goal is optional and external to this skill."
---

# Autopilot

Autopilot is an explicitly authorized long-horizon execution protocol for OpenCode. It is not a primary agent, a replacement for domain skills, a fixed pipeline, or permission to expand scope silently.

<activation_contract>

Enter Autopilot only after the user clearly authorizes execution with language such as "开始 auto 吧", "start autopilot", or "run this unattended". Mentioning autonomy as an idea is not activation.

Before activation, inspect discoverable project facts and settle the few boundaries that materially affect safety or scientific meaning. If the conversation already contains a decision-complete Plan handoff, reuse it rather than interviewing the user again. If a required high-impact boundary is still missing, ask one grouped question before treating the run as activated.

Once activated, do not call `question` until the run terminates or the user interrupts. Resolve reversible ambiguity with the most conservative useful choice and record the assumption. If progress requires an irreversible choice, unavailable credential, new authorization, or unsafe action, stop and write a concrete blocker instead of asking mid-run.

Human messages always supersede unattended execution. Treat an interruption as a request to pause, redirect, or amend the contract before continuing.

</activation_contract>

<flipped_preflight>

## Let The Agent Draft The Goal

Treat the user's first statement as motivation, direction, symptoms, or a desired change rather than mechanically accepting it as the final objective. Autopilot amplifies goal errors, so the agent should bear most of the burden of turning high-level intent into a useful destination.

Before asking the user to specify the task, inspect the project, existing evidence, prior decisions, and relevant constraints. Then teach back a concise current-best interpretation:

- **What I think you actually want:** the underlying outcome or decision, not merely the first proposed implementation.
- **Why this is the right target:** how it connects to the user's motivation and what would change if it succeeds.
- **Success and failure boundary:** evidence that would count as completion, feasibility only, disconfirmation, or unavoidable failure.
- **Autonomy envelope:** what the agent can decide during execution and which side effects remain prohibited.
- **Decisions only the user can make:** scientific values, product tradeoffs, irreversible boundaries, or preferences that artifacts cannot answer.

Offer one reasoned recommended objective by default. Present multiple formulations only when they represent genuinely different high-level values or outcomes; do not dump implementation options. Explain unfamiliar mechanisms and evidence standards in plain language so the user can critique the goal without first becoming the implementation expert.

Separate **goal uncertainty** from **method uncertainty**. Resolve goal uncertainty collaboratively before launch. Leave method choices, experiment design, architecture, hyperparameters, and route exploration to the selected Autopilot profile unless one of them changes the user's intended outcome or authorization boundary.

Ask the user to correct the agent's interpretation, not to fill out a requirements form. After feedback, rewrite the objective, success evidence, non-goals, and autonomy envelope in the agent's own words. Freeze `contract.md` only when this teach-back is stable enough that different reasonable executors would pursue the same high-level outcome.

In `labflow-plan`, prefer this compact discussion shape when it helps:

```markdown
## What I Think You Actually Want
## Why This Is The Right Target
## Success And Failure Boundary
## Autonomy Envelope
## Decisions Only You Can Make
## Autopilot Contract
```

This is goal discovery, not premature execution design. Define where to go without prescribing every step the autonomous loop must take.

</flipped_preflight>

<preflight_contract>

The settled contract must identify:

- one primary profile: `research`, `coding`, or `paper`;
- the high-level objective and evidence that would count as success;
- the agreed topic/artifact root and the repository or manuscript workspace;
- the user-selected Git strategy for this run: current worktree, branch, or isolated worktree;
- writable scope, read-only scope, non-goals, and any authorized high-impact changes;
- wall-clock and compute budget, defaulting to 10 hours only when the user provides no other limit;
- resource constraints for GPUs, CPU, memory, disk, simulators, datasets, and external services;
- commit policy and forbidden external side effects;
- stop conditions and the expected final handoff.

Do not choose the Git/worktree strategy globally. Propose a task-appropriate option from the actual dirty state, data locations, and runtime constraints, then obtain the user's choice during preflight.

If the active agent is `labflow-plan`, remain read-only and produce the decision-complete contract in the proposed plan. Create files and start work only after execution begins under Build.

</preflight_contract>

<artifacts>

After activation, create only these Autopilot-owned files below the user-approved topic root:

```text
.autopilot/
├── contract.md
└── autopilot.md
```

`contract.md` freezes the authorized objective, boundaries, profile, workspace strategy, budget, resource envelope, commit policy, and stop rules. Do not broaden it without a new human instruction.

`autopilot.md` is the living human-readable checkpoint and final handoff. Keep concise sections for current status, active candidate portfolio, currently active PTY/background work, evidence and decisions, the next wave, and final handoff. List only active asynchronous work; after a PTY or subagent completes, integrate its result into evidence and remove it from the active list.

Detailed experiments, casefiles, paper drafts, plots, source changes, decision trees, records, Obsidian notes, README files, and AGENTS files remain owned by their existing project or domain conventions. Update those artifacts when it improves the agreed work, and link them from `autopilot.md`; do not duplicate them under `.autopilot/`.

</artifacts>

<autonomous_loop>

Repeat an adaptive loop rather than a fixed checklist:

1. Orient on current evidence, retained changes, active work, and the highest-level success boundary.
2. Maintain a portfolio of meaningfully different candidate routes before overcommitting to one autoregressive path.
3. Choose the next actions with the highest expected information gain or goal progress.
4. Execute direct work, bounded background subagents, or PTY jobs according to the selected profile.
5. Verify against the relevant evidence ladder, including counterevidence and confounds.
6. Retain, revise, combine, or revert owned changes; preserve independently valid infrastructure fixes separately from failed scientific ideas.
7. Update the domain artifacts and `autopilot.md`, reassess the portfolio, and continue.

When progress stalls, refine the current mechanism, pivot to a genuinely different mechanism, and retrieve focused external evidence before concluding that no defensible next route remains. Do not stop merely because several attempts failed, and do not spend the remaining budget on low-information variants once the plausible route space is exhausted.

</autonomous_loop>

<maximum_useful_parallelism>

Use maximum useful parallelism, not maximum process count.

- Form orthogonal candidate lanes before launch so parallel work reduces anchoring bias rather than duplicating the favored route.
- Parallelize independent retrieval, derivation, code inspection, data preparation, smoke tests, and experiments only when writes, outputs, and evaluation semantics are isolated.
- Before launching runtime probes or experiments, state the expected GPU, VRAM, CPU, RAM, disk, wall-time, and output footprint. Mark uncertain estimates explicitly.
- Inspect relevant live resources such as `nvidia-smi`, process state, memory, and `df`. Start one representative canary when peak use is unknown; after a real startup signal or completed small canary provides evidence, allocate the rest of the candidate wave.
- Do not fill idle hardware for its own sake. Leave appropriate headroom and stop adding jobs when contention would invalidate wall-clock, throughput, memory, randomness, or simulator comparisons.
- Give every parallel lane a disjoint question, write scope or worktree, output root, configuration identity, and expected return. The primary agent owns integration and every long-running process.

</maximum_useful_parallelism>

<event_driven_work>

Use ordinary bounded commands for short work. Use background subagents for independent read-heavy evidence lanes and use PTY sessions for long, interactive, or formal processes.

For each PTY job, set the exact project-local workdir, a descriptive title, `notifyOnExit: true`, and a natural safety timeout when the job should terminate. Record the active session and resource assignment in `autopilot.md`, then continue non-overlapping work. Do not poll with sleep loops. A focused live read is allowed only when current startup evidence is needed for resource allocation or failure diagnosis.

Without a user-started Goal, OpenCode can resume after a background subagent or PTY completion notification, but it cannot wake itself after a response that leaves no asynchronous work. Design experiment-heavy runs as notification-driven chains. For pure coding or writing that needs cross-turn continuation, the user may independently start `/goal`.

Autopilot never creates, pauses, resumes, or completes a Goal. If a user-started Goal is active, background child-session gating may delay continuation until subagents finish. PTY sessions are not child sessions; avoid leaving an active Goal and an active PTY both expecting to drive the next turn.

</event_driven_work>

<git_and_side_effects>

- Respect unrelated dirty changes and stage only Autopilot-owned work.
- Create recovery anchors and meaningful checkpoint commits when they improve recoverability or preserve validated progress.
- Do not commit failed or low-value candidates merely to preserve chronology; record their evidence and discard their owned changes safely.
- During an Autopilot run, do not bump versions, edit release notes as release closure, create release tags, push, publish, deploy, send external messages, purchase resources, rotate credentials, or make production changes unless the frozen contract explicitly authorizes that exact side effect.
- Never use destructive Git recovery against work that was not created by this run.

</git_and_side_effects>

<profiles>

Read exactly one primary profile for the run:

- `references/research.md` for scientific hypotheses, research code, probes, training, evaluation, and evidence-guided method iteration.
- `references/coding.md` for software behavior, implementation, tests, performance, compatibility, and engineering delivery.
- `references/paper.md` for manuscript arguments, claims, citations, figures, analysis, compilation, and reviewer-style iteration.

Profiles are self-contained. They may call existing abilities such as codebase research, literature forensics, PDF reading, image generation, or Git task flow without becoming a second profile.

</profiles>

<stop_and_handoff>

Stop when success evidence satisfies the contract, the user interrupts, the wall-clock/resource budget is exhausted, a safety boundary is reached, an external dependency makes progress impossible, or systematic refinement/pivot/evidence retrieval leaves no defensible next action.

Before stopping, reconcile running PTYs and child tasks, preserve valid outputs, run the strongest affordable final checks, update the topic artifacts, and finish `autopilot.md` with outcomes, decisive evidence, retained commits, failed routes, known limitations, residual risks, and exact reproduction/resume instructions. State clearly when the result is only feasibility evidence rather than formal scientific, engineering, or publication acceptance.

</stop_and_handoff>
