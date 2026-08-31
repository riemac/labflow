# Bounded Probe Protocol

## Purpose

A probe is a small causal intervention designed to separate live hypotheses. It is not a shortened formal run, a parameter sweep, or an excuse to mutate production code.

## Ownership And Parallelism

The primary agent owns probe execution by default because direct command, artifact, and PTY feedback permits faster debugging and immediate bounded iteration. Use ordinary shell execution for commands expected to finish within the tool timeout and a primary-owned PTY/background session for long, interactive, live, or formally tracked work.

Run independent primary-owned probes concurrently only after forecasting CPU, GPU memory, RAM, disk, wall time, and output paths. Inspect current resource and process state, assign disjoint writes and one clear owner per process, then allocate the maximum useful parallel wave without oversubscribing shared resources.

A learning worker may execute a probe only when the coordinator records why preserving worker blindness or lane-local context materially improves the diagnosis and the probe fits the worker limits below. Read-heavy probe design, prediction checks, and source retrieval may still be delegated while execution remains primary-owned.

## Preconditions

Before execution, state:

- one tested hypothesis;
- prediction if true and prediction if false;
- sealed case path and digest;
- frozen inputs, targets, model/checkpoint, and evaluation measure;
- exact changed variable and variables held constant;
- expected information gain;
- wall-time and device budget;
- allowed write paths and cleanup behavior.

Create the skeleton with:

```bash
python3 scripts/case.py new-probe --path <case-root> --id <probe-id> --case case-0001.md
```

## Worker-Owned Hard Limits

- maximum command wall time: 600 seconds;
- maximum simultaneous GPU processes: one;
- write only the assigned probe directory; project-source changes are returned to the coordinator as proposals;
- no formal run directories, checkpoint overwrite, cache pruning, commits, package installation, service changes, or destructive cleanup;
- no PTY; the background worker itself prevents blocking the coordinator.

Use the shell tool's native timeout. On systems with GNU `timeout`, an additional process-level guard such as `timeout --kill-after=20s 600s ...` is useful; other platforms use their native equivalent. Completion notifications replace sleep/poll loops.

## Isolation Level

The default boundary combines the agent write contract, host workspace sandbox, command permissions, and probe-local paths. A Python probe still has the operating-system access granted by its host sandbox. When a probe consumes untrusted code or requires stronger filesystem/process isolation, the coordinator chooses an available container or sandbox such as bubblewrap and records that boundary in the manifest.

## Probe Artifacts

- `manifest.yaml`: case identity, hypothesis, command, cwd, environment boundary, seed, budget, inputs, writes, start/end, exit status, and artifacts;
- `plan.md`: mechanism and true/false predictions written before execution;
- `scripts/`: durable analysis or tiny-experiment code;
- `artifacts/`: small structured outputs, plots, or summaries;
- `result.md`: observation, interpretation, counterevidence, and decision consequence.

Disposable intermediates belong under the probe-local `.tmp/` directory or the host's platform temporary directory. Every fact supporting a conclusion retains a durable source or is copied into the probe artifact with provenance.

## Interpretation

A successful tiny overfit establishes local function and optimization capacity only. A frozen readout establishes decodability under that probe class, not mutual information or downstream transfer. A negative probe can be caused by insufficient probe capacity, poor conditioning, or bad implementation. Always report what the probe cannot establish.

If a worker-owned command reaches its limit, requires additional devices, changes formal scientific configuration, or needs project-wide edits, stop and return the blocker to the coordinator. The primary may design a larger authorized probe or formal experiment instead of stretching the worker contract.
