---
name: git-task-flow
description: "Git task-flow management skill for semantic implementation tasks: task-start anchors, checkpoint commits, diff review, history cleanup, final semantic commits, and SemVer/VERSION/CHANGELOG/release-tag closure for repositories or self-contained subprojects."
---

# Git Task Flow

Use this skill for meaningful implementation or documentation tasks that need recoverable git boundaries, checkpoint commits, semantic history cleanup, and version-aware task closure.

## When To Use

- Starting a task that should have a clear git recovery anchor.
- Reviewing the real worktree before or after edits.
- Creating checkpoint commits for recoverability.
- Fixing leaked, mixed, or patch-like commits before finalizing.
- Closing a task as a clean semantic commit or small semantic commit series.
- Updating `VERSION` / `CHANGELOG` when the task has versioned semantic output.

## Core Rules

1. At task start, create a recovery tag, usually `task/<name>/<YYYYMMDD>`.
2. Treat `task/...` tags as recovery anchors, not release/version tags.
3. Check `git status` before staging, and use `git diff` to verify the real changes.
4. Use conventional commit messages for checkpoint and final commits.
5. Intermediate commits are checkpoints. They do not imply final history and must not trigger version bumps by themselves.
6. Do not mix unrelated local edits into the task commit. If unrelated changes exist, leave them unstaged and mention them.
7. If the task depends on simulation, visualization, experiments, or human research judgment, do not treat it as finally accepted until the user confirms the result.
8. If verification fails after a checkpoint commit, keep the checkpoint and continue fixing; do not destructively rewind.
9. Never use `git reset --hard` or destructive checkout/reset commands unless the user explicitly asks.

## Version Closure

When a user explicitly uses `git-task-flow`, assume the task is intended to produce at least patch-level semantic progress once it is truly closed.

At task close:

- Judge whether the completed task is `patch`, `minor`, or `major` for each relevant versioned surface.
- If the change is `patch`, update the relevant `VERSION` / `CHANGELOG` by default and include that update in the final semantic commit.
- If the change is `minor` or `major`, pause and ask the user to confirm the bump before editing version files or creating release tags.
- Write `CHANGELOG` entries as human/agent-readable semantic task summaries, not per-commit logs.
- Keep the newest version section near the top; read recent top sections by default unless older history is needed.
- Keep version closure tied to the accepted task result, not to every checkpoint commit.

Use this SemVer interpretation:

- `patch`: fixes, documentation, tests, cleanup, small behavior corrections, or internal refactors that do not change the public contract.
- `minor`: new capabilities or changed user-visible behavior/API/contracts that remain acceptable within the current compatibility story.
- `major`: breaking changes to public APIs, persisted formats, generated artifact semantics, or workflow contracts after the project has a stable major line.

For `0.x` research projects, breaking contract changes usually map to `minor` unless the repository already defines stricter release rules.

## Repository And Subproject Versions

- Repository-level release tags, such as `v0.2.1`, bind to repository-level version files and changelogs.
- A self-contained subproject may maintain its own `VERSION` / `CHANGELOG` even before it becomes a package, submodule, or independently tagged release surface.
- Do not force subproject git tags, submodules, or package metadata unless the repository already uses them or the user asks.
- If a task bumps a subproject version and the repository also has a top-level version, prefer a repository `patch` bump unless project docs say otherwise or the user chooses not to.
- A release tag should point to the commit that already contains the corresponding `VERSION` / `CHANGELOG` state.

## Release Tag Closure

- When a repository already uses release tags, every accepted release commit with a new `VERSION` and Changelog section must receive the corresponding `v${VERSION}` tag before version closure is complete.
- Create the release tag only after the final semantic commit is validated; task/checkpoint tags never substitute for release tags.
- Before creating a tag, verify that the name is absent locally and remotely, the target commit contains the expected version state, and the target is on the intended release history.
- Follow the repository's existing lightweight-versus-annotated tag convention. Never move or replace an existing release tag without explicit user approval.
- Push release tags only when the user explicitly authorizes remote publication, then verify the remote target after pushing.
- For audited legacy releases that predate a VERSION file, a backfilled tag may point to the commit that finalized the corresponding Changelog release boundary; record this as a historical exception.
- If no commit represents an exact version state, document the version as skipped instead of assigning a misleading tag or rewriting shared history.

## History Cleanup Principles

- Treat commits as semantic boundaries, not a pure time log.
- If a later edit belongs in an earlier semantic commit, fold it back with `git commit --amend`, `fixup`, or an interactive rebase when safe.
- Prefer squashing patch-like tail commits into the commit they repair.
- Keep genuinely independent task phases as separate commits.
- Before rewriting local history, create a recovery anchor if one does not already exist.
- Avoid rewriting shared history unless the user explicitly chooses that tradeoff.

## Useful Commands

- `git status --short`
- `git diff`
- `git diff --staged`
- `git log <task-tag>..HEAD --oneline`
- `git commit --amend`
- `git rebase -i <base>`
- `git reset --soft <tag-or-commit>`
- `git cherry-pick <commit>`
- `git stash push -u`

## Recommended Flow

1. Start: inspect status and create a `task/...` recovery tag if appropriate.
2. During work: make checkpoint commits only at clear recovery points.
3. Before staging: review unstaged and staged diffs; keep unrelated changes out.
4. Before final commit: decide the semantic commit boundary and whether history cleanup is needed.
5. Version closure: judge `patch` / `minor` / `major`; auto-apply `patch`, ask for `minor` / `major`.
6. Finalize: commit the accepted code/docs/version changes; for a true release/version closure, create and verify the matching release tag, then push it only with explicit user authorization.
7. Report: summarize final commit(s), version changes, validation, and any unrelated worktree changes left untouched.
