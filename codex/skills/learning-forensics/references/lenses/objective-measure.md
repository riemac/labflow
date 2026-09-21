# Lens: Objective, Estimator, And Statistical Measure

## Causal Question

What population quantity does the implemented objective actually optimize, and does that quantity reward the intended scientific behavior?

## Required Evidence

Write the exact per-sample formula, transformations, normalization, configured weights, masks, denominators, reduction order, estimator, baselines, regularizers, and aggregation population. Preserve numerator/denominator sufficient statistics when valid counts differ. Distinguish raw loss, normalized loss, selection metric, evaluation metric, and physical outcome.

## Failure Mechanisms

- easy or structural-zero samples dominate useful active signal;
- averaging order changes morphology/domain/task weighting;
- target scale, normalization, clipping, or robust loss hides meaningful error;
- surrogate objective admits constant, shortcut, or mode-collapsed solutions;
- advantage, return, contrastive, variational, or self-training estimator is biased or high variance;
- masks silently shrink valid support;
- training objective and evaluation population disagree;
- weighted total falls while one required component remains at baseline.

## Evidence And Controls

Compare against explicit naive/oracle baselines under the identical reduction. Report component losses, prediction and target moments, valid counts, active/zero or easy/hard branches, strata, and tolerance curves. Recompute from dense evidence when possible and test invariance to batch partition or aggregation order.

## Decisive Probes

Baseline-normalized skill, active-only versus balanced reduction, per-sample reweighting audit, fixed sufficient-statistic parity, alternative proper scoring rule on frozen predictions, and objective-value checks on hand-constructed predictions.

## Do Not Overclaim

Changing objective weights cannot create absent information. Lower surrogate risk does not guarantee the intended physical, generative, or control behavior. A baseline comparison is meaningful only when population and reduction are identical.
