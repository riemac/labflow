# Human-First Dossier Layout

```text
<dossier>/
|-- README.md
|-- brief.md
|-- MAP.md
|-- search-log.md
|-- bibliography.bib
|-- topics/
|   `-- <lane>.md
|-- papers/
|   |-- <citekey>.md
|   `-- <citekey>.pdf
`-- .state/
    |-- workers.json
    `-- literature-cache.sqlite
```

## Ownership

- Coordinator only: `README.md`, `brief.md`, `MAP.md`, `bibliography.bib`.
- One worker only: each assigned `topics/<lane>.md` and its paper cards.
- CLI only: SQLite cache and generated raw graph data.
- Coordinator through CLI: `workers.json`.

## Human Entry Point

`README.md` should answer, without opening the cache:

- What question is being investigated?
- What is the current bounded answer?
- Which lanes are active or complete?
- Which papers require lead verification?
- What is the next checkpoint?
- Where are the map, bibliography, and search coverage?

## Git Policy

- Track Markdown, BibTeX, templates, and curated conclusions.
- Ignore `.state/` because task IDs and caches are machine-local.
- Ignore `papers/*.pdf` by default to avoid accidental large binary commits.
- Keep PDF and paper card basename identical so the dossier remains self-contained
  and easy to browse locally.

## Update Rules

- Workers write synthesized topic notes, not raw search dumps.
- The coordinator exports a readable `search-log.md` at checkpoints.
- Only exact, close, and counterevidence papers need full paper cards by default.
- Preserve exclusion reasons so future sessions do not repeat the same screening.
