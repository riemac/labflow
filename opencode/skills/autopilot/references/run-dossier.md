# Autopilot Run Dossier

Use one new dossier for each explicitly activated Autopilot run. The dossier is a compact semantic authority and convergence record, not a duplicate process log, TODO database, experiment archive, or Git history.

## Layout

```text
<topic-root>/.autopilot/<UTC-timestamp>-<semantic-slug>/
├── .gitignore
├── manifest.json
├── source.md
├── contract.md
├── envelope.md
├── amendments/
│   └── A0001-<slug>.md
├── phases/
│   ├── current.md
│   └── P0001-<slug>.md
├── reviews/
│   ├── R0001.md
│   └── probes/R0001/
└── outcome.md
```

The run-local `.gitignore` contains exactly `*`, keeping every dossier local without changing the enclosing repository's ignore rules. Version accepted project artifacts outside the dossier according to the sealed Git policy.

## Document Ownership

- `source.md` preserves the approved proposed plan and later user instructions that materially settle semantics. It is provenance, not a raw transcript.
- `contract.md` states the human-level intent, success and failure boundary, fixed decisions, non-goals, method freedom, and human judgment gates.
- `envelope.md` states the execution profile, workspace, write boundary, Git policy, human-readable resource envelope, positive Goal limits (`max_turns`, `max_duration_ms`, and `max_tokens`), side-effect authorization, and stop conditions. Never store credential values.
- `amendments/` contains only explicitly user-authorized changes to effective authority. Ordinary questions, implementation decisions, failed methods, and evidence-driven pivots are not amendments.
- `phases/current.md` is the one mutable semantic phase. It describes what semantic uncertainty or outcome matters now, why, its entry and exit evidence, and allowed pivots. Native TODOs own command-level work.
- Closed `phases/P####-*.md` files are immutable evidence-bearing phase records. Close one phase before changing authority or opening the next.
- `outcome.md` is the complete candidate handoff assessed by the convergence reviewer and finalized only after approval.
- `manifest.json` is the deterministic machine identity. Do not edit it manually.

PTY state comes from `pty_list` and the Goal-PTY gate. Background-agent identity comes from OpenCode child sessions. TODO state comes from `todowrite`. Repository state comes from Git and actual artifacts. Do not mirror these sources into another Autopilot runtime file.

## CLI

Resolve bundled paths relative to the skill directory, not the shell working directory:

```bash
python3 scripts/autopilot.py -h
python3 scripts/autopilot.py run init -h
python3 scripts/autopilot.py authority seal -h
python3 scripts/autopilot.py phase open -h
python3 scripts/autopilot.py review open -h
python3 scripts/autopilot.py goal render -h
```

Every leaf command documents its inputs and side effects. Use `--json` for a compact versioned result. Diagnostics go to stderr. Only commands with an explicit `--stdin` flag read stdin.

Stable exits are `0` for success, `1` for a valid but unmet lifecycle precondition, `2` for usage or content-schema errors, `3` for an integrity violation, and `4` for local I/O failure.

## Lifecycle

1. Run `run init`, then author `source.md`, `contract.md`, and `envelope.md` in the discussion language.
2. Run `authority seal`; from this point direct changes fail validation.
3. Run `phase open`, author `phases/current.md`, and use `goal render --json` to obtain the bounded Goal projection.
4. At an information-bearing phase boundary, finish the phase outcome and next-phase rationale, run `phase close`, re-read effective authority, and either open the next phase or prepare convergence.
5. For an explicit user semantic change, close the current phase, run `amendment new`, author the draft, then run `amendment seal` before opening another phase.
6. At convergence, complete `outcome.md`, run `review open`, then launch or resume the one Autopilot reviewer task. The reviewer calls `autopilot_review_attest` first so the host validates the run and binds its actual session identity.
7. Record the reviewer's strict JSON through `review record --stdin`. Probe reservation and review recording share one lock; if a reviewer host dies after reserving a probe, use `review recover` only after its recorded PID identity is gone and deadline expired. Rejection opens another remediation phase; approval permits `run finalize` only while authority and outcome bytes remain unchanged.
8. Submit `goal_complete` only after `run finalize` succeeds.

## Integrity

Authority sealing hashes the exact bytes of `source.md`, `contract.md`, and `envelope.md`. Each amendment extends the authority head as `SHA256(previous_head + "\n" + amendment_sha256)`. Closed phases and recorded reviews retain their own digests. Finalization requires the latest approved review to bind the current authority head and exact outcome digest.

The CLI detects accidental or silent mutation; it is not an adversarial sandbox. A hash mismatch pauses autonomous work until the authority is restored or the user explicitly authorizes an amendment.

## Goal Projection

`goal render` extracts stable marker-delimited sections so generated documents may use the discussion language without changing machine parsing. It emits `objective`, `successCriteria`, `constraints`, `mode: normal`, and the three positive Goal budget fields from the sealed envelope, and refuses text output beyond the Goal plugin's 4000/2000/2000 character limits.

Use `goal_set` once when the run has no matching Goal. If a user-created Goal already represents the same run, preserve its original text in `source.md`, then update its objective with the rendered projection. At later phase transitions update only the objective. Never complete a Goal for a phase-level result.
