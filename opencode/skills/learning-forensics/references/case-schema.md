# Blind Casefile Schema

## Contract

A casefile is a sealed, fact-only snapshot shared by all first-round workers. It defines the problem they investigate without transmitting the coordinator's favored explanation.

Use the numbered path `.learning/cases/case-XXXX.md`; `seal-case` checks identity and non-empty required sections, changes `status` from `draft` to `sealed`, and creates the adjacent `.sha256` identity. Every worker assignment records both path and digest.

## Required Shape

```markdown
---
schema_version: 1.0.0
case_id: case-0001
status: draft
created: YYYY-MM-DD
---

# Blind Casefile

## Case Identity
Experiment/run/checkpoint identities, code revision, dirty state, resume lineage, dataset/task/simulator versions, hardware, software, and completion state.

## Decision To Support
One bounded scientific or engineering decision. Do not encode the preferred answer.

## Frozen Observations
Raw or explicitly derived observations with formula, population, mask, denominator, units, window, and source artifact.

## Case-Specific Causal Chain
Concrete nodes and transformations, their authoritative definitions, and missing links. Use `not-yet-assessed`, not healthy/broken labels.

## Authoritative Design Sources
Project instructions, formulas, configs, schemas, source, tests, and the portions of distributed prompts that define intended behavior. A file mixing design intent with diagnostic speculation belongs in the withheld list unless the coordinator extracts a fact-only design excerpt into the sealed case.

## Available Evidence
Pointers and identities for event files, JSONL, NPZ, manifests, checkpoints, evaluation reports, profiler traces, qualitative outputs, and external sources.

## Withheld Diagnosis Sources
Existing tuning notes, speculative reports, and coordinator hypotheses excluded from the blind first pass.

## Constraints And Safety
Active runs, immutable artifacts, compute budget, allowed devices, write roots, privacy, and human-judgment boundaries.

## Missing Facts
Required quantities not yet measured or unidentifiable from current artifacts.
```

## Observation Discipline

Label every derived value with its exact formula. A final-window mean must state window bounds and weighting. A baseline-normalized skill must identify the baseline population and formula. A visual impression is an observation only after the source figure, axes, smoothing, and raw data boundary are stated.

Do not include causal words such as "because", "caused by", "likely due to", or "the problem is" unless they quote an authoritative design contract. Those statements belong after blind evidence collection.

## Revision Rule

Never modify a sealed case. When a material fact changes, create the next numbered case, explain what evidence was added, seal it, and explicitly resume or restart workers against the new digest. Small report edits that do not alter worker evidence should stay outside the casefile.
