# Learning Worker Assignment Schema

Use this contract for every new or resumed `learning-worker` task.

```yaml
case_root: <absolute dossier path>
casefile:
  path: <case_root>/.learning/cases/case-0001.md
  sha256: <sealed digest>

worker_state:
  worker_id: <stable logical owner>
  runtime_handle: <task or thread handle after launch>
  lane_owner: <unique lane path owner>

phase: blind-audit | cross-examination | probe
profile: fast | normal | deep
language: <research language>

primary_lens: <stable lens name>
causal_span:
  from: <upstream node or edge>
  to: <downstream node or edge>
question: <one bounded causal question>
decision_connection: <why this answer changes the coordinator's decision>

limits:
  max_probe_wall_seconds: 600
  max_gpu_processes: 1
  max_external_sources: <integer>

scope:
  include: <artifacts, code, mechanisms, populations, or systems>
  exclude: <explicit boundaries>
  authoritative_design_sources: <paths>
  withheld_diagnosis_sources: <paths>

write_targets:
  lane_audit: <case_root>/.learning/audit/lanes/<lens>.md
  probe_root: <case_root>/.learning/probes/<probe-id> or none
```

## Profiles

- `fast`: inspect the most direct authoritative evidence and return once the bounded causal question has a sufficient answer; no experiment and no broad external search.
- `normal`: trace the relevant contracts, artifacts, implementation, and immediate alternatives; cross-check the central conclusion and propose one decisive probe.
- `deep`: systematically test alternative mechanisms, boundary cases, cross-node dependencies, and counterexamples while remaining bounded by the assigned lens.

Profile controls investigative depth. Phase controls whether experimentation is allowed. A worker must never promote its own phase or profile.

## Lens Semantics

`primary_lens` is emphasis, not a ban on adjacent evidence. Cross an upstream or downstream boundary when it is necessary to establish causality, but identify the evidence as cross-lane and keep the return centered on the assigned question. Do not silently take over another worker's topic.

## Blindness

For `blind-audit`, keep coordinator hypotheses and other worker findings outside the assignment. The worker reads the sealed case and listed authoritative sources; paths under `withheld_diagnosis_sources` remain outside scope. If an old diagnosis appears accidentally, mark the contamination and independently reconstruct the mechanism from primary evidence.

For `cross-examination`, provide the competing claims and decisive evidence explicitly. For `probe`, provide a previously created probe root and complete safety contract.

## Return Contract

Return research content in the assigned language:

1. direct answer to the bounded question;
2. decisive facts with exact paths, steps, formulas, units, and provenance;
3. at most three falsifiable hypotheses, each with mechanism;
4. strongest supporting and contradictory evidence;
5. cross-lane evidence that another investigation should consider;
6. missing or unidentifiable evidence;
7. one decisive test with predictions if true and false, cost, intrusion, and confidence;
8. exact claims the coordinator should verify before acting.

Write detailed recovery evidence to the assigned lane or probe artifact, but do not foreground task IDs, retrieval narration, raw logs, or budget telemetry in the parent return.

## Continuation

Record the returned task/thread handle in coordinator-owned `workers.json`. Resume the same worker for the same lens and evidence chain, including transitions from blind audit to cross-examination or probe. Start a new worker for a different lens, independent verification, or a stale/noisy context. The worker does not delegate further.
