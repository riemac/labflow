# Lens: Evaluation And Experiment Design

## Causal Question

Does the evidence measure the intended capability on the intended population, and what smallest experiment can distinguish the remaining causal explanations?

## Required Evidence

Define estimand, split, population, metric formula, units, aggregation, checkpoint selection, budget coordinate, seed structure, confidence, and human-judgment boundary before ranking runs. Audit completion, resume segments, baseline identity, data leakage, evaluation frequency, and whether the test set influenced selection.

## Failure Mechanisms

- training proxy improves while meaningful outcome stays flat;
- checkpoint, smoothing, window, or seed is selected post hoc;
- candidates use different data, compute, environment distribution, model size, or evaluation budget;
- global means hide tail-domain regression;
- asynchronous episodes or variable denominators bias aggregation;
- evaluation is too noisy, too small, contaminated, or outside deployment support;
- a negative result is uninformative because the experiment changes several causal links at once.

## Evidence And Controls

Use raw traces, explicit baselines, paired units, morphology/domain/task strata, seed-level results, fixed-budget alignment, frozen evaluation distributions, predeclared selection rules, and confidence intervals or bootstrap appropriate to the sampling hierarchy.

## Decisive Experiment Design

For each live hypothesis specify intervention, controlled variables, metric, population, predicted outcome if true and false, cost, code intrusion, contamination risk, and stopping rule. Prefer one experiment that separates several hypotheses over several loosely informative runs.

Typical high-information probes include deterministic formula tests, tiny fixed-set overfit, frozen readout, oracle input, task-only/joint comparison, matched optimizer ablation, intervention/shuffle, and held-out transfer.

## Do Not Overclaim

One seed is descriptive. A best checkpoint on the test set is not held-out evidence. Smooth curves are not numerical summaries. Simulation or qualitative visual outcomes require researcher inspection. "No improvement" is not a diagnosis unless the experiment isolates a causal link.
