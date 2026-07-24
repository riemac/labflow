# Literature Worker Assignment Contract

Use this compact contract for every new or resumed `literature-worker` task.
The coordinator should explicitly fill every field; the worker may infer a
missing profile only as a recovery behavior.

```yaml
research_root: <absolute research directory>
brief: <research_root>/.research/brief.md
lane: <stable lane name>
question: <one bounded scientific question>
decision_connection: <why this lane matters>

profile: fast | normal | deep
language: <research output language>
limits:
  max_full_papers: <non-negative integer>

scope:
  include: <settings, mechanisms, and work types>
  exclude: <explicit boundaries>
  allowed_local_sources: <paths or none>
  seed_identifiers: <identifiers or none>

write_targets:
  lane_audit: <research_root>/.research/audit/lanes/<lane>.md
  paper_audit_directory: <research_root>/.research/audit/papers/
```

## Profiles

- `fast`: search and provider recommendations; inspect title, metadata, candidate abstracts, and targeted key pages; never complete a full-PDF read or traverse citation graphs.
- `normal`: supplemental search, selected primary-source pages, complete PDF reading of the strongest selected candidates, and no more than one citation hop from the initial seed set.
- `deep`: no broad discovery; completely read only explicitly named core-paper PDFs.

`max_full_papers` defaults are `fast: 0`, `normal: 3`, and `deep: 5`. It counts only unique papers newly completed at `review.worker: full`: the PDF must be downloaded and verified, the complete main body read, and the method, experiments/results, limitations/discussion, and all lane-relevant appendices checked. Downloading or opening a PDF does not count. Titles, metadata, abstracts, citation edges, and targeted page checks are uncounted candidate evidence and never contribute to a researched/read/reviewed paper count. A task must not promote itself within an assignment. Resume the same task for the same lane and evidence chain; the coordinator may issue a new assignment with a different profile, including a transition from discovery to deep full-PDF reading. Two consecutive searches without a new high-relevance candidate end the discovery phase.

## Return

Return research content, not process telemetry:

1. direct answer to the lane question;
2. three highest-impact findings with paper names;
3. strongest counterevidence or uncertainty;
4. primary pages or figures the lead should verify;
5. unresolved scientific question, if one remains.

Do not foreground task IDs, artifact paths, API failures, query logs, or budget
accounting. Write those details to the assigned hidden audit artifacts when
they are necessary for recovery.
