# Lens: Runtime, Infrastructure, And Numerics

## Causal Question

Does the machine execute the intended mathematical training process faithfully, reproducibly, and within the declared resource boundary?

## Required Evidence

Trace data loading, preprocessing, cache, sharding, device transfer, dtype/autocast, compilation, forward/backward, accumulation, synchronization, distributed reduction, clipping, optimizer step, checkpoint, resume, evaluation, and artifact writing. Record hardware/software identity, shapes, memory, throughput, and failure markers.

## Failure Mechanisms

- mixed-precision underflow/overflow or unintended TF32/casting;
- microbatch, distributed, or gradient-accumulation denominator mismatch;
- detached graph, unused parameter, stale activation, donated buffer, or compiler semantic change;
- wrong device, asynchronous timing, missing synchronization, data starvation, or hidden host transfer;
- cache identity mismatch, stale artifacts, race, incomplete write, or corrupted resume;
- duplicated/skipped samples, workers, steps, or event segments;
- checkpoint loads partial or incompatible namespaces;
- systems bottleneck changes effective data distribution or update cadence.

## Evidence And Controls

Use deterministic contract tests, full-versus-streamed parity, precision-matched batches, checksums, step/sample accounting, resume replay, non-finite scans, optimizer-state inspection, profiler traces after stable timing, and artifact completion/lineage gates.

## Decisive Probes

Single-update parity, FP32 versus mixed-precision comparison, compile on/off fixed-batch parity, checkpoint roundtrip, exact replay from an epoch boundary, cache audit, throughput timeline, and per-stage memory/time boundary measurement.

## Do Not Overclaim

A runtime contract passing proves execution fidelity, not learning quality. A faster path that changes masks, samples, outputs, precision semantics, or update frequency is a method change. Exit code zero is not enough without completion artifacts and expected budgets.
