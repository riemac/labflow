# Lens: Architecture And Function Class

## Causal Question

Assuming the required information reaches the model, can the declared architecture and readout represent, route, and condition the intended mapping at usable numerical scale?

## Required Evidence

Recover exact architecture, parameter partition, routing/selectors, receptive field, attention or message-passing graph, activation and normalization, initialization, output constraints, capacity, and which modules receive each objective gradient. Verify shape tests with semantically adversarial cases, not only nominal tensors.

## Failure Mechanisms

- insufficient receptive field, depth, rank, width, memory, or interaction order;
- incorrect token/entity/query/owner/action routing;
- bottleneck or pooling destroys correspondence;
- output activation, initialization, or bilinear factorization creates dead/small paths;
- parameter sharing imposes incompatible symmetries or task coupling;
- padding/masks permit leakage or suppress valid entities;
- decoder or critic absorbs training signal while retained modules stay uninformative.

## Evidence And Controls

Trace dependencies from each required input to each output and gradient path. Inspect activations, output ranges, parameter and gradient spectra, dead units, selector perturbations, and simple synthetic functions known to require the intended interaction. Compare a direct oracle readout and a higher-capacity diagnostic without changing the target.

## Decisive Probes

Single-example memorization, single-factor synthetic mapping, frozen-input reader-only training, routing shuffle, rank/interaction ablation, direct concatenation oracle, and layer/module replacement under fixed data and objective.

## Do Not Overclaim

Parameter count is not function-class evidence. Tiny-overfit success does not prove population adequacy. A larger diagnostic reader can reveal information but may violate deployment cost or retained-artifact constraints.
