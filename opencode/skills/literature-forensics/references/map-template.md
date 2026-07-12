# Curated Literature MAP Template

`MAP.md` is a human-curated semantic map, not the complete citation graph. Keep
only nodes that affect the research decision.

```md
---
graph_id: <topic>
title: <title>
status: active
updated: 2026-07-10
search_cutoff: 2026-07-10
---

# <Title> MAP

## Research Question

<One bounded question.>

## Graph

```mermaid
flowchart TD
  Q000["<b>Q000 Research question</b>"]
  M010["<b>M010 Candidate mechanism</b>"]
  T100["<b>T100 Prior-art lane</b>"]
  P110["<b>P110 Exact or close paper</b>"]
  C120["<b>C120 Counterevidence</b>"]
  G200["<b>G200 Candidate gap</b>"]

  Q000 -->|candidate mechanism| M010
  M010 -->|searched in| T100
  T100 -->|strong evidence| P110
  T100 -->|challenges| C120
  P110 -->|setting/mechanism mismatch| G200
  C120 -->|narrows| G200

  classDef question fill:#d9eaf7,stroke:#2f6f9f,stroke-width:2px,color:#111;
  classDef exact fill:#d8f5d0,stroke:#3a7a2a,stroke-width:2px,color:#111;
  classDef close fill:#fff2cc,stroke:#a66f00,stroke-width:2px,color:#111;
  classDef background fill:#e6e6e6,stroke:#666,stroke-width:1px,color:#333;
  classDef counter fill:#f4cccc,stroke:#990000,stroke-width:2px,color:#111;
  classDef gap fill:#d9d2e9,stroke:#674ea7,stroke-width:2px,color:#111;

  class Q000 question;
  class P110 exact;
  class T100 close;
  class C120 counter;
  class G200 gap;
```

## Node Index

| Node | Artifact | Class | Evidence depth | Meaning |
|---|---|---|---|---|
| T100 | [topic](topics/example.md) | close | targeted | ... |
| P110 | [topic evidence](topics/example.md#core-works) | exact | lead targeted | ... |

## Evidence Diagnosis

## Novelty Boundary

## Candidate Next Searches

## Map Invariants

- Promote only screened evidence into the map.
- Link every paper/topic node to its artifact.
- Keep exact, analogue, background, and counterevidence visually distinct.
- State the search cutoff for every absence-based inference.
```

Store raw graph and audit evidence under `.research/`; never auto-overwrite the
curated human map with machine output.
