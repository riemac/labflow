# Research Profile

Use this profile when the primary outcome is a scientific or algorithmic conclusion, a validated method, an experiment-backed feasibility decision, or a research implementation whose meaning depends on evidence rather than software completion alone.

## Research Contract

Ground the run in the object of study, intended mechanism, evaluation estimand, baseline, authoritative design sources, available evidence, formal success boundary, and approved compute/data envelope. Preserve units, coordinate frames, dataset splits, seeds, checkpoints, simulator versions, and other identities that affect interpretation.

Research may include substantial engineering. Source changes, infrastructure repairs, profiling, data tooling, and experiment orchestration are allowed inside the contract because they support scientific evidence; they are not automatically scientific contributions.

## Candidate Portfolio

Before committing to one route, form a portfolio with genuinely different mechanisms rather than cosmetic hyperparameter variants. Include conservative, ambitious, and high-risk candidates when each is plausible. Use independent background evidence lanes when they can reduce anchoring bias, but give every lane the same factual problem boundary without leaking the favored answer.

Prune candidates using first-principles constraints, counterexamples, invariants, code/system fit, and the smallest discriminative observation. Preserve negative evidence so discarded mechanisms are not repeatedly rediscovered.

## Evidence Ladder

Advance only as far as the current evidence supports:

1. mathematical, physical, statistical, shape, unit, coordinate, and implementation invariants;
2. static checks, synthetic fixtures, gradient/data-flow probes, and tiny deterministic examples;
3. runtime smoke tests proving only that the path executes and artifacts close correctly;
4. small-scale candidate comparisons with explicit confound control;
5. robustness checks such as multiple seeds, held-out data, ablations, calibration, or transfer when relevant;
6. formal experiments within the frozen budget and evaluation contract.

Passing one rung authorizes the next rung only when the contract permits its resources. A runnable path is not evidence of a valid learning signal; a small improvement is not a formal result; a selected checkpoint is not unbiased evaluation unless the selection protocol supports that claim.

## Resource-Aware Waves

Forecast each experiment's likely resources and scientific comparability. Run a representative canary before parallel allocation when peak memory or runtime is unknown. Partition GPU IDs, output roots, seeds, caches, and configuration identities explicitly. Serialize jobs when contention changes the measured quantity; parallelize derivation, retrieval, data preparation, or work on other independent hardware instead.

Within the approved resource budget, autonomously scale a supported route from probe to formal experiment without asking again. Stop escalation when prerequisite evidence fails, the formal metric is confounded, or the remaining budget cannot answer the decision honestly.

## Decide And Record

For every candidate wave, compare predicted and observed behavior, inspect failure modes, separate method failure from infrastructure failure, and choose whether to retain, repair, combine, or discard. Keep independently valid infrastructure improvements as their own checkpoints even when the method that exposed them fails.

Maintain the project's existing research documents, decision tree, record, casefile, experiment manifests, plots, and artifact lineage. End with the strongest supported conclusion, counterevidence, failed mechanisms, retained code/commits, formal run identities, unresolved scientific boundaries, and a clear distinction between feasibility and accepted evidence.
