# Research Brainstorm Method Card

Use this reference when a brainstorm needs a durable, reviewable structure. Keep cards compact; delete fields that do not help the decision.

## Method Card

```md
### <method name>

**Core idea.** One or two sentences.

**Mechanism.** Explain why the method could work from geometry, physics, statistics, representation, optimization, or data-distribution pressure.

**Key assumptions.**
- ...

**Counterexamples / failure modes.**
- ...

**Minimal validation probe.**
- Dataset / environment:
- Intervention:
- Metric:
- Expected signal if the idea is right:
- Fast rejection criterion:

**Cost / risk / novelty.**
- Engineering cost:
- Experimental cost:
- Risk:
- Novelty hypothesis:

**Fit to current project.**
- Required code/data changes:
- Compatibility with existing pipeline:
- What it would unblock:
```

## Candidate Buckets

```md
| Bucket | Meaning | Candidates |
|---|---|---|
| safe | Conservative, likely useful, low novelty | ... |
| promising | Best near-term research bet | ... |
| risky | High upside, heavy assumptions | ... |
| do-not-do | Attractive but likely misleading or too costly | ... |
```

## Minimal Probe Quality Bar

A useful probe should be:

- **small** enough to run before full implementation;
- **mechanistic** enough to test the core assumption, not just final performance;
- **falsifiable** with a clear rejection signal;
- **connected** to the user’s actual task and artifacts.
