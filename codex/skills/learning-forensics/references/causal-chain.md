# Case-Specific Learning Causal Chain

## Purpose

The chain is a scientific accounting device: it makes every required transformation explicit so the investigation can locate the earliest unsupported transition. It is not a universal architecture diagram and must be adapted to the actual learning setting.

## Default Template

$$
\text{Data / Task}\rightarrow\text{Signal / Target}\rightarrow\text{Observable Input / Experience}\rightarrow\text{Representation}\rightarrow\text{Function Class}\rightarrow\text{Objective / Estimator}\rightarrow\text{Gradient}\rightarrow\text{Update}\rightarrow\text{Behavior / Prediction}\rightarrow\text{Evaluation}
$$

Add preprocessing, simulator dynamics, replay, augmentation, search, sampling, decoding, or deployment nodes when they are causally material. Merge nodes only when their evidence and failure modes are genuinely inseparable.

## Feedback Systems

For reinforcement learning, online learning, active learning, self-training, and model-generated data, represent the case as a directed causal graph with explicit feedback. A minimal RL loop is:

$$
\text{policy}\rightarrow\text{trajectory / replay distribution}\rightarrow\text{return or advantage estimator}\rightarrow\text{gradient and update}\rightarrow\text{policy}
$$

Attach environment dynamics, observation history, exploration, reward/termination, value bootstrap, target networks, replay age, and evaluation distribution where relevant. Record which quantities are on-policy, off-policy, delayed, bootstrapped, clipped, or held fixed. A policy-induced distribution shift is an edge in the learning mechanism, not background noise.

## Paradigm Mappings

| Setting | Data / task | Signal / target | Objective / estimator | Behavior / evaluation |
| --- | --- | --- | --- | --- |
| Supervised | dataset and split | label or structured target | empirical risk and regularizer | prediction on declared population |
| Unsupervised | observed distribution | density, reconstruction, clustering, or latent structure assumption | likelihood, divergence, reconstruction, or contrastive estimator | sample quality, structure, or downstream utility |
| Self-supervised | raw samples and view generator | pretext relation or teacher signal | contrastive, masked, predictive, or distillation objective | retained information and transfer |
| Generative | training distribution and conditioning | score, noise, likelihood, preference, or reconstruction signal | variational, adversarial, diffusion, autoregressive, or preference estimator | generated distribution under a declared sampler |
| Reinforcement learning | MDP/POMDP, simulator, reset, exploration, trajectory/replay distribution | reward, cost, return, advantage, bootstrap, demonstration, or preference | on/off-policy policy/value/model objective and estimator | closed-loop behavior feeding the next data distribution plus frozen-distribution evaluation |

## Node And Edge Contract

For each node record the concrete object, owner, source paths, schema, units, shapes, population, masks, stochasticity, and version identity. For each edge record what information is expected to cross, the mathematical or algorithmic transformation, assumptions required, and direct evidence that the transformation is faithful.

An edge can fail even when both endpoint tensors exist. A representation may have the right shape but omit target-relevant information; an objective may be finite but optimize a different population; a gradient may be nonzero but directionally incoherent; an update may execute but be canceled by clipping, moments, stale data, or nonstationarity.

## Earliest-Break Discipline

Downstream symptoms do not identify upstream causes. If labels are inconsistent, optimizer ablations cannot establish a representation failure. If the target is not observable from permitted inputs, a larger decoder cannot solve the intended problem without leakage. If evaluation changed population, a flat score cannot identify optimization failure.

Conclude at the earliest link for which evidence supports failure while upstream links remain sufficiently credible. When upstream evidence is missing, report the competing links rather than skipping ahead.
