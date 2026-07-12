# Human And Audit Research Layout

```text
<research>/
|-- README.md
|-- overview.md
|-- MAP.md
|-- topics/
|   |-- README.md
|   `-- <topic>.md
`-- .research/
    |-- brief.md
    |-- audit/
    |   |-- papers/
    |   |-- lanes/
    |   |-- exclusions.md
    |   `-- verification.md
    |-- library/
    |   `-- <citekey>.pdf
    |-- search-log.md
    |-- bibliography.bib
    `-- state/
        `-- workers.json
```

## Human Layer

- `README.md` is a short navigation page.
- `overview.md` answers the cross-topic research question and explains priority
  threats, evidence boundaries, and a recommended reading path.
- `MAP.md` is a human-curated semantic evidence map, never a raw graph dump.
- Each `topics/<topic>.md` is a complete researcher-facing report: current
  answer, taxonomy, core works, conflicting evidence, relation to the user's
  research, unresolved questions, and recommended source locations.
- Do not create a visible paper-card directory. Integrate important paper-level
  analysis into topic reports.

## Audit Layer

- Workers write only assigned files under `.research/audit/lanes/` and
  `.research/audit/papers/`.
- Local PDFs live under `.research/library/` and are normally gitignored.
- Search coverage, exclusions, verification queues, BibTeX, and task state stay
  under `.research/`.
- Litnav owns its global SQLite cache; no literature cache belongs in a dossier.

## Ownership

- Coordinator only: all human-facing files and central audit summaries.
- One worker only: each assigned lane audit and paper audit card.
- Coordinator only: `.research/state/workers.json`.
- Litnav: global metadata cache outside the research directory.

## Mechanical Maintenance

Use `scripts/research.py` only for initialization, v1 migration, and structural
validation. It must not synthesize findings or rewrite scientific conclusions.
