# Human Topic Report

## Purpose

A topic report is a complete researcher-facing explanation of one dimension that materially affects the case. It is not a worker transcript, artifact inventory, or generic checklist. Create topics dynamically after evidence shows they matter.

## Recommended Shape

```markdown
# <Topic Title>

> [!abstract] Current answer
> State the bounded conclusion, confidence, and evidence boundary in plain language.

## Current Answer
Expand the abstract when the reasoning needs more context.

## System Contract
Define the relevant data, equations, interfaces, populations, units, and intended causal role.

## What The Evidence Shows
Present decisive measurements, comparisons, figures, and source paths. Define every derived metric.

## Mechanism
Explain from first principles why the evidence supports or weakens each causal explanation.

## Counterevidence And Boundary
Give the strongest alternative explanation, counterexample, missing evidence, and what is not established.

> [!question] Major unresolved question
> Name the uncertainty whose answer would most change the diagnosis.

## Decisive Probes Or Intervention
Describe the smallest next action, predicted outcomes, cost, and how the decision changes.

> [!important] Key action
> Highlight the intervention the researcher should review or authorize next.

## Evidence Locations
List concise auditable paths, checkpoints, commands, figures, papers, or upstream sources.
```

## Paper Flavor

Use equations, diagrams, and domain terminology when they clarify mechanism, but explain them in complete readable prose. Preserve physical units and statistical estimands. State whether evidence is training-only, held-out, transfer, systems, simulation, or qualitative.

Integrate important worker-level findings instead of linking the reader into hidden audit files. Keep task IDs, provider failures, search attempts, command chatter, and speculative brainstorms out of the human report.

## Assets

An asset used in a report should preserve its source data or locator, generation script/command, axis labels, units, legend, caption, and whether smoothing or filtering was applied. Visual evidence requiring human judgment remains explicitly unconfirmed until the researcher inspects it.
