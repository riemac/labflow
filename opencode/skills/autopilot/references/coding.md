# Coding Profile

Use this profile when the primary outcome is correct, maintainable, verified software behavior: a feature, fix, migration implementation, performance improvement, cleanup, or engineering delivery.

## Engineering Contract

Identify observable acceptance criteria, affected users/callers, compatibility expectations, writable scope, forbidden side effects, and the commands that establish the current baseline. Inspect distributed prompts, tests, schemas, registration paths, and similar implementations before choosing an approach.

Ordinary source edits, tests, internal refactors, and related engineering repairs are autonomous inside the contract. New dependencies, public API or schema changes, persisted-data migration, credential handling, deployment, and production effects are forbidden unless preflight explicitly authorizes them.

## Choose The Work Shape

Do not force a candidate portfolio onto an obvious local fix. Implement directly when evidence identifies one narrow defect. When architecture, performance, compatibility, or algorithm choice remains ambiguous, form independent candidates and compare the smallest prototypes or benchmarks that distinguish them.

A coherent engineering intention may span multiple files. Parallel implementation requires disjoint modules or isolated worktrees and a defined integration boundary; do not let multiple lanes edit the same contract without one owner.

## Verification Ladder

Move from narrow to broad evidence:

1. reproduce the existing failure or record the baseline;
2. run focused unit/contract tests, type checks, static analysis, or a minimal benchmark;
3. exercise relevant integration paths and failure cases;
4. run the strongest affordable related and full suites;
5. inspect the final diff for accidental scope, compatibility, security, and maintainability regressions.

Do not hide failures, weaken tests to fit an implementation, or treat compilation as behavioral acceptance. If a performance claim matters, control warmup, hardware contention, sample count, and measurement variance.

## Retain And Integrate

Keep changes that satisfy acceptance with an acceptable complexity and compatibility cost. Revert owned failed candidates without touching pre-existing work. Preserve useful infrastructure fixes or test improvements separately when they are valid independent of the rejected route.

Create meaningful checkpoint commits for recoverable, validated milestones. Do not perform version release closure, tags, push, deployment, or publication during the Autopilot run.

Update existing implementation docs, README/AGENTS guidance, generated artifacts, or migration notes only when the code change makes them stale. End with exact acceptance evidence, retained commits, API/compatibility implications, performance results, limitations, and reproducible verification commands.
