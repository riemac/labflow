# Lens: Representation

## Causal Question

Does the learned or engineered representation preserve the information, structure, and sensitivities required by the downstream target or behavior without relying on forbidden shortcuts?

## Required Evidence

Define representation inputs, token/entity semantics, dimensions, masks, pooling, temporal context, invariances, retained versus disposable components, and downstream access. Inspect statistics by meaningful entity/domain strata and compare checkpoints, layers, and random initialization.

## Failure Mechanisms

- constant, low-rank, anisotropic, saturated, or numerically collapsed features;
- shortcut information bypasses the intended representation;
- pooling or compression discards local, signed, temporal, relational, or derivative information;
- invariance removes information that the target should transform equivariantly;
- representation specializes to frequent domains and fails tail structures;
- pretext objective is solved by a feature irrelevant to transfer;
- leakage makes probes look good without legitimate information.

## Evidence And Controls

Measure variance, covariance/effective rank, norms, pairwise geometry, layerwise evolution, perturbation sensitivity, and matched/shuffled correspondence. Use frozen linear and nonlinear probes, but keep input conditions and evaluation populations explicit. Compare full fine-tune, frozen encoder, random encoder, and oracle representation controls when relevant.

## Decisive Probes

Frozen-layer readouts, same-sample versus shuffled-latent decoding, entity/token intervention, low-rank replay, targeted perturbation response, and downstream transfer under matched architecture and budget.

## Do Not Overclaim

Linear-probe failure does not prove information absence; probe capacity and conditioning matter. Nonlinear-probe success proves decodability by that probe, not that the trained reader or optimizer can use the information. High feature variance does not establish semantic sufficiency.
