# Lens: Observability And Problem Mechanism

## Causal Question

Can the intended target or behavior be inferred from the variables the learner is permitted to observe, under the domain's physical, statistical, or decision-process mechanism?

## Required Evidence

List permitted inputs and deliberately excluded/privileged variables, temporal horizon, coordinate frames, symmetries, latent state, downstream availability, and the mathematical dependence of the target or optimal action. Identify equivalence classes of inputs that produce different targets.

## Paradigm Mapping

- supervised: whether $p(y\mid x)$ is concentrated enough for the declared loss and metric;
- self-supervised: whether the pretext relation requires information that views preserve and downstream tasks need;
- generative: whether conditioning and context identify the intended distribution mode;
- RL/POMDP: whether observation/history is sufficient for state estimation, credit assignment, and optimal control;
- physics/robotics: whether geometry, kinematics, dynamics, contact, or object state needed by the target enters the allowed input.

## Failure Mechanisms

- unobserved confounder or hidden state;
- target depends on future, privileged simulator state, unavailable identity, or longer history;
- symmetry makes sign, permutation, orientation, or correspondence unidentifiable;
- lossy preprocessing destroys the decisive coordinate or scale;
- target is well-defined physically but not conditionally predictable from the retained variables;
- nonstationary policy/data collection changes the conditional relation.

## Counterevidence And Controls

Construct paired examples with identical allowed inputs and differing targets, or prove why they cannot exist. Add oracle variables one at a time, compare memoryless and history-aware probes, test coordinate rewrites, and check whether a simple explicit mechanism model can predict the target.

## Decisive Probes

Oracle-feature readout, conditional-variance estimation, same-observation/different-target search, history-length ablation, intervention on one latent physical variable, and invariance/equivariance paired tests.

## Do Not Overclaim

Failure of one neural probe does not prove information-theoretic impossibility. Low global correlation does not prove non-observability. Conversely, memorizing identifiers can make a target predictable while violating the intended generalization contract.
