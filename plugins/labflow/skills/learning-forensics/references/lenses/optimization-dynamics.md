# Lens: Optimization Geometry And Training Dynamics

## Causal Question

Does the implemented gradient and update process extract a stable population direction from the objective and move parameters in a way that improves the intended behavior?

## Required Evidence

Recover optimizer, learning-rate schedule, moments/state, weight decay, clipping, accumulation, task balancing, parameter groups, frozen modules, update-to-parameter ratios, checkpoint/resume state, and nonstationary data or curriculum events. Inspect directions and actual loss changes, not only norms.

## Failure Mechanisms

- vanishing, exploding, sparse, noisy, or batch-incoherent gradients;
- task gradients conflict, or balancing normalizes low-signal noise into a large update;
- clipping, mixed scales, moments, weight decay, or scheduler suppress useful motion;
- stale optimizer state or resume mismatch changes dynamics;
- private and shared parameter groups receive unintended objectives;
- learning rate is too small for progress or too large for stable descent;
- curriculum, replay, policy, teacher, or data distribution moves faster than optimization;
- delayed credit assignment, bootstrap error, stale target networks, importance-weight mismatch, or policy lag rotates the effective RL update;
- apparent convergence is a constant predictor, saturation, or optimizer limit cycle.

## Evidence And Controls

Measure layer/group norms, cosine, dot products, effective weighted contributions, clipping ratios, update/parameter ratio, batch-to-batch direction consistency, gradient signal-to-noise, Adam moment scales, and one-step predicted versus realized loss change. Align all quantities to the same population and denominator.

## Decisive Probes

Fixed-batch repeated updates, task-only versus joint training, plain normalized sum versus balancing method, frozen-module optimization, gradient accumulation parity, small learning-rate line search, moment reset diagnostic, direction-coherence windows, frozen-policy advantage audits, and matched on/off-policy replay checks.

## Do Not Overclaim

Equal contribution norms do not imply equal information quality. Negative task cosine does not prove harmful interference. A task-only improvement may result from changed data or denominator unless all other variables are held fixed. Optimizer replacement is downstream of target and observability checks.
