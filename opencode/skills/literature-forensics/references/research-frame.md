# Research Hunch Frame

Use this frame before retrieval. Keep it concise enough to become the shared
brief for every worker.

## Decision

- What decision must this investigation support?
- What would change if an exact prior work is found?
- What evidence would make the idea worth an experiment?

## Research Hunch

| Field | Entry |
|---|---|
| Phenomenon | Observed or suspected behavior. |
| Candidate mechanism | Mathematical, optimization, physical, statistical, or systems explanation. |
| Setting | Tasks, environments, assets, embodiments, datasets, or populations. |
| Intervention | Proposed algorithmic or engineering response. |
| Novelty axis | The intersection that may be underexplored. |
| Counter-hypothesis | A plausible reason the phenomenon or mechanism is wrong. |

## Search Semantics

- Exact terms:
- Historical or neighbouring terms:
- Mechanism aliases:
- Setting aliases:
- Intervention aliases:
- Likely implementation/library terms:

## Scope

- Include:
- Exclude:
- Allowed local files/directories:
- Seed papers:
- Date/venue constraints:

## Budget And Stop Rule

- Metadata candidates per lane:
- Abstract screens per lane:
- Targeted/full reads per lane:
- Citation depth per round: one hop by default.
- Stop when:

## Clarification Prompts

Ask only questions that alter the investigation. Useful prompts include:

- Is the novelty hypothesis about the mechanism, the robotics setting, their
  combination, or the engineering system that makes the experiment possible?
- Should work with different topology/action spaces count as direct prior art or
  only as a setting analogue?
- Does demonstration/offline data change comparability?
- Is an implementation-level failure mode sufficient, or must the work contain
  formal analysis?
- Which local notes and paper directories are explicitly in scope?
