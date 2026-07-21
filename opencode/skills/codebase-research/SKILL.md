---
name: codebase-research
description: "Use when an agent needs to inspect a local repository before answering or editing: trace architecture, locate symbols, follow call chains/data flow, find similar implementations, inspect config registration paths, or decide which files to read/change. Use parallel shell probes, key-file reads, and subagent prefetch. Not for external docs, papers, or third-party API research."
---

## Default Loop

Aim to quickly identify the files and code paths that matter for the current task.

Use **MAX PARALLELISM** aggressively: split the task into independent branches, then run shell probes and obvious file reads in parallel. Do not wait for one search to finish before launching other independent searches.

1. **Shell narrowing**: use `tree` for structure, `fdfind` for file discovery (prefer over plain `find`), and `rg` for symbols/config keys/strings (prefer over plain `grep`). Use depth limits and excludes for caches, dependencies, generated files, logs, outputs, and data when useful.
2. **Read key files**: verify behavior in entry points, definitions, registration sites, one caller/callee layer, similar implementations, and relevant tests/examples. If key paths are already known, read directly; do not force exhaustive search first.

Example shell probes:

```bash
tree target_dir -L 3 -a -I '.git|__pycache__|.venv|node_modules|dist|build|logs|outputs'
fdfind 'reward|manager|cfg' target_dir
rg -n "RewardManager|RewTerm|RewardsCfg" target_dir
```

## Subagent Delegation

Follow the global **Background-First Prefetch** protocol when delegating. This
section only defines codebase-specific triggers and outputs: use the built-in
`explore` subagent for unfamiliar subsystems, cross-module chains, or multiple
candidates likely to consume the main context.

- Prefer focused scopes, but allow one subagent to cover several related modules when the question is inherently cross-module.
- Ask for useful paths, line references, likely entry points, and remaining uncertainty.
- Treat findings as high-signal prefetch; verify exact code details that drive the next answer or edit.

## Avoid

- Workspace-wide searches without path scoping.
- Dumping huge directory trees without depth limits/excludes.
