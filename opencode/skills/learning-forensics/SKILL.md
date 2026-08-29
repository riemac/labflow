---
name: learning-forensics
description: Use when a supervised, unsupervised, self-supervised, generative, reinforcement-learning, or robotics learning system plateaus, diverges, collapses, overfits, underperforms a baseline, behaves unexpectedly, or needs evidence-driven tuning. Builds a case-specific learning causal chain, coordinates hypothesis-blind parallel learning-worker investigations, identifies the earliest broken link, and designs bounded discriminative probes. Do not use for routine curve plotting, a simple known error, or autonomous large-scale hyperparameter sweeps.
---

# Learning Forensics

<mission>

Investigate failed learning behavior as a causal scientific problem rather than a bag of hyperparameters. The central question is:

> Given a failed learning behavior, what is the earliest broken link in the learning chain?

The default chain is:

$$
\text{Data / Task}\rightarrow\text{Signal / Target}\rightarrow\text{Observable Input / Experience}\rightarrow\text{Representation}\rightarrow\text{Function Class}\rightarrow\text{Objective / Estimator}\rightarrow\text{Gradient}\rightarrow\text{Update}\rightarrow\text{Behavior / Prediction}\rightarrow\text{Evaluation}
$$

This is a template, not a mandatory pipeline. Adapt, split, merge, or rename nodes to match supervised learning, unsupervised learning, self-supervision, generative modeling, reinforcement learning, robotics, or another learning setting. Diagnose the earliest unsupported transition before tuning downstream machinery.

</mission>

<coordinator_contract>

The calling primary agent is the research lead and final evidence owner. It must:

- independently inspect the project contracts, code, run artifacts, and current process state;
- frame the failed behavior and the decision the investigation must support;
- construct the case-specific causal graph from objective facts;
- keep facts, observations, hypotheses, inferences, proposed interventions, and accepted decisions distinct;
- freeze a hypothesis-free casefile before the blind worker round;
- choose genuinely useful primary lenses, launch workers in the background, and continue non-overlapping investigation;
- verify exact evidence that drives a diagnosis or code change;
- resolve conflicts between workers and own every human-facing report;
- select the smallest probe that distinguishes live hypotheses;
- ask before any formal, expensive, intrusive, or long-running experiment.

Workers increase coverage and provide independent causal readings. They do not replace the primary agent's scientific reasoning, choose the final diagnosis, or write the researcher-facing synthesis.

</coordinator_contract>

<causal_model>

## Build The Case-Specific Chain

Read `references/causal-chain.md` only when the setting needs additional mapping examples. For each active node and transition, record:

- the concrete object in this project;
- the authoritative formula, interface, configuration, or source path;
- inputs, outputs, units, shapes, masks, denominators, populations, budgets, and invariances;
- available direct evidence and provenance;
- missing or unidentifiable evidence.

Do not mark a node as broken in the blind casefile. For example, record the exact optimizer and gradient aggregation formula, not "the optimizer probably amplifies noise." Record a flat metric against a declared baseline, not "the representation collapsed."

Feedback settings such as reinforcement learning, online learning, active learning, self-training, and model-generated data should close the relevant loop explicitly rather than forcing the case into a static chain. Record how behavior changes the next experience distribution and estimator.

## Apply First-Principles Lenses Everywhere

Every causal span should be challenged through the relevant mathematical and scientific lenses:

- identifiability and observability: can the permitted variables determine the target or behavior?
- information sufficiency: what information must survive each representation or estimator?
- symmetry, invariance, equivariance, gauge, and coordinate conventions;
- support and measure: what population is sampled, weighted, masked, and evaluated?
- dimensional analysis, scale, conditioning, normalization, and numerical range;
- bias, variance, stochastic noise, label or reward noise, and gradient signal-to-noise;
- causal interventions, counterfactuals, negative controls, and plausible counterexamples;
- differentiability, discontinuities, estimator assumptions, and approximation error.

A large loss, gradient, or update norm is not evidence of useful information. A decreasing training scalar is not evidence that the intended population behavior was learned.

</causal_model>

<case_protocol>

## Create Or Resume A Dossier

Read `references/dossier-layout.md`. Initialize or validate a local-only case directory with the standard-library helper:

```bash
python3 scripts/case.py init --path <case-root> --language <language> --title "<title>" --question "<bounded question>"
python3 scripts/case.py validate --path <case-root> --json
```

When invoked outside this skill directory, use the absolute path to `scripts/case.py`. The helper requires Python 3.9 or newer and owns deterministic structure only; it never diagnoses learning behavior or runs experiments.

## Build And Seal The Blind Casefile

Create a numbered case draft, fill it with objective facts, then seal it:

```bash
python3 scripts/case.py new-case --path <case-root>
python3 scripts/case.py seal-case --path <case-root> --case case-0001.md
```

Read `references/case-schema.md`. A blind casefile may contain the symptom, decision, causal-graph contracts, authoritative design sources, observations, invariants, evidence pointers, constraints, and missing facts. It must not contain the coordinator's favored cause, a ranked hypothesis list, tuning advice, or worker conclusions.

Separate source classes explicitly:

- `authoritative_design_sources`: project instructions, formulas, configs, schemas, source code, and distributed design prompts that define intended behavior;
- `withheld_diagnosis_sources`: existing tuning notes, prior speculative reports, and coordinator hypotheses that blind workers should not read during their first pass.

All first-round workers receive the same sealed case path and SHA-256. If material facts change, create and seal a new numbered case instead of editing the old one.

</case_protocol>

<parallel_investigation>

## Select Primary Lenses

The standard first-round candidate lenses are:

1. data, signal, target, teacher, reward, and experience distribution;
2. observability, identifiability, problem mechanism, and domain assumptions;
3. learned or engineered representation and information retention;
4. architecture, routing, inductive bias, and function-class capacity;
5. objective, estimator, masks, reduction, baseline, and statistical measure;
6. gradient geometry, optimizer dynamics, scheduling, clipping, and multi-task updates;
7. precision, accumulation, distributed execution, resume, cache, runtime, and systems infrastructure;
8. evaluation validity, comparison fairness, checkpoint choice, and discriminative experiment design.

These are lenses, not permanent departments. A lens defines emphasis rather than a prohibition on adjacent evidence. Remove irrelevant lenses, add a case-specific lens when needed, and avoid duplicate assignments. For a genuinely new and poorly understood learning failure, up to eight independent blind workers may run concurrently; later work should resume only the high-information lanes.

## Delegate Blind First Passes

Read `references/assignment-schema.md`. Each assignment must include the sealed case, worker ownership state, phase, primary lens, causal span, bounded question, decision connection, profile, scope, limits, write targets, and research language. Do not include the coordinator's preferred explanation.

Use the Task tool with `subagent_type: learning-worker` and `background: true`. Continue non-overlapping work while workers run. Resume the same `task_id` for the same lens and evidence chain; do not poll or duplicate their investigation.

Record every returned task ID in `.learning/state/workers.json`. Each blind worker returns at most three falsifiable hypotheses, including mechanism, supporting evidence, contradictory evidence, missing evidence, and a decisive test with predictions under both outcomes. It also writes only its assigned hidden lane artifact.

## Cross-Examine Instead Of Voting

After the blind returns, compare mechanisms and evidence rather than counting how many workers agree. Build a conflict table:

- claim;
- supporting sources;
- strongest counterevidence;
- causal-graph location;
- whether the claim explains all observed symptoms;
- evidence that would falsify it.

Resume the relevant worker when its existing context remains useful. Provide competing evidence during `cross-examination`; do not preserve blindness after the first pass. Start a new worker only for a genuinely different lens or independent verification.

</parallel_investigation>

<probe_and_tuning>

## Prioritize Information, Not Parameter Motion

Rank probes qualitatively by high expected information gain and low compute cost, wall time, code intrusion, and contamination risk. If a numeric score is useful, first normalize every component to a dimensionless case-local scale:

$$
S=\frac{\widehat I}{\epsilon+w_c\widehat C+w_t\widehat T+w_r\widehat R+w_x\widehat X}
$$

Prefer probes that split competing explanations: deterministic formula checks, fixed-batch audits, tiny overfit, frozen-module readouts, oracle features, intervention or shuffle tests, gradient-direction consistency, matched optimizer ablations, and held-out evaluation under a frozen population.

Do not jump from a flat loss to a new optimizer, larger model, or longer training budget. First determine whether the failure lies in data or signal, observability, representation, function class, objective, gradient, update, runtime, or evaluation.

## Bounded Worker Probes

Read `references/probe-protocol.md`. Resume the original worker with `phase: probe` only after stating:

- the hypothesis being tested;
- predictions if true and if false;
- exact inputs and frozen evidence;
- the isolated probe write target;
- maximum wall time of 600 seconds;
- at most one GPU process;
- stop and cleanup conditions.

The worker uses ordinary shell execution with a hard timeout. It writes scripts, durable results, and disposable intermediates under `.learning/probes/<probe-id>/`. Project-source changes are returned as proposals for the primary agent. Formal runs, checkpoints, caches, commits, and formal training budgets remain outside the worker's ownership.

## Long Or Formal Experiments

The primary agent owns every long-running or formal experiment. Ask the user before launch, preserve a versioned scientific configuration, use a separate output root, and record the command and lineage. On OpenCode, use an available PTY/background-session tool according to the global rules. On Codex, use the host's native background process facility when available. Never delegate process ownership to a generic subagent or poll with shell sleep.

</probe_and_tuning>

<synthesis_and_reporting>

## State The Earliest Supported Break

The conclusion should identify one of:

- earliest broken link supported by current evidence;
- a bounded set of unresolved competing links;
- evidence insufficient because a required quantity is unidentifiable.

Distinguish local capacity, optimization, population learning, generalization, transfer, and systems performance. A successful tiny overfit proves local capacity, not generalization. A valid runtime proves execution, not learning. A low training loss proves neither identifiability nor downstream utility.

## Maintain Human And Audit Layers

The primary agent writes:

- `overview.md`: current cross-topic diagnosis, evidence boundary, earliest supported break, confidence, and next decision;
- `topics/*.md`: complete paper-flavor reports for the dimensions that matter in this case;
- optional `assets/`: plots, diagrams, or tables with captions and provenance.

Read `references/topic-report.md`. Do not pre-create empty generic topics. A topic report should explain the system contract, mechanism, evidence, counterevidence, unresolved boundary, and decisive next action without exposing task IDs or raw worker narration.

Workers write only assigned files under `.learning/audit/lanes/` and `.learning/probes/`. The coordinator owns hidden central state, cross-examination, decision tree, record, and all human-facing files.

</synthesis_and_reporting>

<routing>

Read only what the current phase requires:

- exact fact-only case format: `references/case-schema.md`;
- dossier ownership and layout: `references/dossier-layout.md`;
- full worker assignment and return schema: `references/assignment-schema.md`;
- human topic structure: `references/topic-report.md` or `references/topic-report_CN.md`;
- bounded experiment rules: `references/probe-protocol.md`;
- focused external implementation, docs, or paper evidence: `references/external-evidence.md`;
- scientific depth for one primary lens: the corresponding file under `references/lenses/`.

</routing>

<anti_patterns>

- Do not return a generic learning-rate, batch-size, depth, optimizer, and regularization checklist.
- Do not expose a favored hypothesis to every blind worker.
- Do not launch eight workers with semantically duplicate questions.
- Do not let worker agreement substitute for evidence.
- Do not interpret raw loss without baseline, denominator, population, unit, and prediction behavior.
- Do not infer information quality from gradient magnitude alone.
- Do not treat a project-local diagnostic skill as interchangeable with this coordinator method.
- Do not run a new formal budget before cheaper causal probes are exhausted.
- Do not let workers write human-facing synthesis or shared central state.
- Do not claim a simulation, visualization, or qualitative behavior passed without researcher inspection.

</anti_patterns>
