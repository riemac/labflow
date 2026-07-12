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
  max_new_papers: <non-negative integer>
  max_primary_reads: <non-negative integer>

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

- `fast`: search and provider recommendations; inspect title, metadata, and all
  candidate abstracts; never open paper bodies or traverse citation graphs.
- `normal`: supplemental search, selected primary-source pages, and no more than
  one citation hop from the initial seed set.
- `deep`: no broad discovery; deeply analyze only explicitly named core papers.

Defaults are `fast: 10/0`, `normal: 8/5`, and `deep: 0/3` for
`max_new_papers/max_primary_reads`. A task must not promote itself to another
profile. Two consecutive searches without a new high-relevance candidate end
the discovery phase.

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
