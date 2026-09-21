---
name: codebase-research
description: "Use when an agent needs to inspect a local repository before answering or editing: trace architecture, locate symbols, follow call chains/data flow, find similar implementations, inspect config registration paths, or decide which files to read/change. Use scoped shell probes, key-file reads, and bounded explore-worker prefetch when it protects the main context. Not for external docs, papers, or third-party API research."
---

## Default Loop

Aim to quickly identify the files and code paths that matter for the current task.

Run independent shell probes and obvious file reads in parallel when that shortens the same bounded investigation. Do not split one coherent code path into redundant searches merely to maximize parallelism.

1. **Shell narrowing**: use `tree` for structure, `fdfind` for file discovery (prefer over plain `find`), and `rg` for symbols/config keys/strings (prefer over plain `grep`). Use depth limits and excludes for caches, dependencies, generated files, logs, outputs, and data when useful.
2. **Read key files**: verify behavior in entry points, definitions, registration sites, one caller/callee layer, similar implementations, and relevant tests/examples. If key paths are already known, read directly; do not force exhaustive search first.

Use `rg -n --heading` to avoid repeating long paths; use `--no-heading` or `--json` when downstream tooling needs self-contained records.

Example shell probes:

```bash
tree target_dir -L 3 -a -I '.git|__pycache__|.venv|node_modules|dist|build|logs|outputs'
fdfind 'reward|manager|cfg' target_dir
rg -n --heading "RewardManager|RewTerm|RewardsCfg" target_dir
```

## Subagent Delegation

Follow the global exploration profile and **Background-First Prefetch** contract when delegating. Use `explore-worker` for unfamiliar subsystems, cross-module chains, alternate naming, or multiple candidate implementations likely to consume the main context. Read known files or inspect a small number of targets directly.

- Pass `profile`, target paths or exclusions, known symbols, the code question, and the expected paths/line references in the assignment. Default to `normal`.
- Prefer one worker for one call chain or subsystem; use parallel workers only for independent code paths.
- Treat findings as high-signal prefetch; verify exact code details that drive the next answer or edit.

## Avoid

- Workspace-wide searches without path scoping.
- Dumping huge directory trees without depth limits/excludes.
