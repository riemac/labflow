# Learning-Forensics Dossier Layout

```text
<case-root>/
|-- .gitignore
|-- README.md
|-- overview.md
|-- topics/
|   |-- README.md
|   `-- <dynamic-topic>.md
|-- assets/                         # optional figures, tables, and diagrams
`-- .learning/
    |-- brief.md
    |-- evidence-index.yaml
    |-- decision-tree.md
    |-- record.md
    |-- cases/
    |   |-- case-0001.md
    |   `-- case-0001.md.sha256
    |-- audit/
    |   |-- cross-examination.md
    |   `-- lanes/<lens>.md
    |-- probes/
    |   `-- <probe-id>/
    |       |-- manifest.yaml
    |       |-- plan.md
    |       |-- scripts/
    |       |-- artifacts/
    |       `-- result.md
    `-- state/
        |-- workers.json
        `-- processes.json
```

## Investigation Identity And Continuity

Create this dossier only after Learning Forensics is formally activated. One dossier follows one learning object and one stable decision semantics across new checkpoints, metrics, local hypotheses, probes, and modest shifts in causal focus. These ordinary developments update the existing dossier rather than creating sibling dossier roots.

Sealed numbered casefiles are immutable blind-input snapshots inside that continuing investigation. Create the next snapshot only when a later blind round needs materially updated facts. Cross-examination, worker continuation, probe results, and narrowed hypotheses normally reuse the current dossier without another snapshot. Start a new dossier only when the model/task/data object or core decision changes materially, or when the user explicitly asks for separation.

## Human Layer

- `README.md` is short navigation and status only.
- `overview.md` states the current cross-topic answer, earliest supported break, confidence, evidence boundary, and next decision.
- `topics/*.md` are complete paper-flavor reports created only for dimensions that matter to this case.
- `assets/` is optional. Every figure or table used in a report should have a caption, source data, generation command or script, and units.

The coordinator owns the human layer. Workers never draft or edit it.

## Hidden Agent Layer

- `brief.md` stores the stable question, decision, language, and safety boundary.
- `cases/` stores immutable blind evidence snapshots.
- `evidence-index.yaml` points to source artifacts and identities; do not duplicate large run directories.
- `decision-tree.md` and `record.md` are agent-facing causal and chronological state, not researcher reading material.
- each lane file has one worker owner at a time;
- each probe directory is isolated and tied to one sealed case digest;
- `workers.json` is coordinator-owned task/thread ownership and continuation state.
- `processes.json` is coordinator-owned PTY/background-process identity, command lineage, case digest, optional probe ID, GPU assignment, and completion state.

Update central state and reports at information-bearing transitions such as a new sealed snapshot, decisive worker return, completed probe, changed causal boundary, or accepted decision. Command-by-command narration and routine PTY status changes are not required dossier events.

## Git Boundary

A new dossier is local-only: its root `.gitignore` contains `*`, so the entire dossier remains outside the enclosing worktree. Do not modify the enclosing project's ignore rules. Move an accepted report outside the dossier only when the user explicitly wants it versioned or shared.

## Concurrent Ownership

Several workers may run concurrently only with disjoint lane or probe write targets. They must return proposed central changes to the coordinator. A worker must never edit `brief.md`, casefiles, evidence index, decision tree, record, cross-examination, worker state, overview, topics, or another worker's lane.
