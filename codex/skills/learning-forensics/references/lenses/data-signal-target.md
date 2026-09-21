# Lens: Data, Signal, And Target

## Causal Question

Does the learning system receive a correct, stable, representative, and sufficiently informative signal over the intended population?

## Paradigm Mapping

- supervised: examples, labels, annotator process, split, class/structure distribution;
- unsupervised/generative: observed support, corruptions, augmentations, negatives, noise schedule, conditioning data;
- self-supervised: view generator, teacher or pseudo-label, masking, temporal relation, positive/negative definition;
- reinforcement learning: observation and transition distribution, exploration coverage, reward/cost, termination, reset, on/off-policy support, replay age or rollout sampling, demonstrations/preferences;
- simulation/robotics: assets, geometry, physics parameters, domain randomization, oracle/teacher computation, validity regions.

## Required Evidence

Recover dataset/task identity, generation code, split leakage boundary, sample counts, weighting, invalid/missing rates, target units and sign, noise and stochasticity, provenance, cache identity, and transformations between stored and consumed values. Inspect representative dense samples and tail strata, not only global moments.

## Failure Mechanisms

- wrong formula, sign, frame, unit, index, time alignment, or owner/routing;
- target undefined, discontinuous, ambiguous, or high variance on common support;
- class/domain/asset imbalance or sampling support mismatch;
- label, reward, teacher, or simulator noise exceeding conditional signal;
- leakage, duplicate identities, stale cache, augmentation inconsistency, or train/eval overlap;
- reward shaping or termination producing an unintended behavior proxy;
- policy-induced distribution shift, weak exploration support, or replay mismatch hiding the state-action region where improvement is required;
- masks removing difficult samples and making the metric look solved.

## Counterevidence And Controls

Use deterministic hand cases, analytic or finite-difference checks, repeated realization of identical inputs, independent reference implementations, shuffled-label controls, structural-zero checks, target histograms by meaningful strata, and exact cache/source audits.

## Decisive Probes

Fixed-example target replay, tiny oracle dataset, target-only baseline, same-input repeated teacher evaluation, per-stratum noise-to-signal estimates, and controlled removal of one augmentation or sampling mechanism.

## Do Not Overclaim

A balanced marginal target distribution does not imply conditional predictability. Teacher agreement on average does not validate tail regions. A tiny-overfit failure does not by itself prove bad data; architecture and optimization may still be responsible.
