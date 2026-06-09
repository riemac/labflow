---
name: codebase-research
description: "Use when Codex needs to inspect a local repository before answering or editing: trace architecture, locate symbols, follow call chains/data flow, find similar implementations, inspect config registration paths, or decide which files to read/change. Use path-scoped local semantic retrieval, parallel shell probes, key-file reads, and subagent prefetch. Not for external docs, papers, or third-party API research."
---

## Default Loop

Aim to quickly identify the files and code paths that matter for the current task.

Use max parallelism aggressively: split the task into independent branches, then run semantic retrieval, shell probes, and obvious file reads in parallel. Do not wait for one search to finish before launching other independent searches.

1. **Semantic retrieval (prefer first)**: use the current local semantic/code-RAG tool as the primary entry point. Query one concept at a time. Always scope to the narrowest defensible repo/subproject/module path; re-scope deeper as evidence appears. Follow the active tool's own skill/docs for query style.
  > now the semantic tool is ccc, refer to ccc skill when needed
2. **Shell narrowing**: use `tree` for structure, `fd` for file discovery (`fdfind` alias; prefer over plain `find`), and `rg` for symbols/config keys/strings (prefer over plain `grep`). Use depth limits and excludes for caches, dependencies, generated files, logs, outputs, and data when useful.
3. **Read key files**: verify behavior in entry points, definitions, registration sites, one caller/callee layer, similar implementations, and relevant tests/examples. If key paths are already known, read directly; do not force semantic search.

Example shell probes:

```bash
tree target_dir -L 3 -a -I '.git|__pycache__|.venv|node_modules|dist|build|logs|outputs|.cocoindex_code'
fd 'reward|manager|cfg' target_dir
rg -n "RewardManager|RewTerm|RewardsCfg" target_dir
```

## Subagent Delegation

Keep delegation separate from the default loop. Use it as prefetch: if unfamiliar subsystems, cross-module chains, or multiple candidates are likely to consume main context, launch scoped subagents early while the main agent continues local search/read work.

- Prefer narrow scopes, but allow one subagent to cover several related modules when the question is inherently cross-module; split independent branches into parallel subagents.
- Ask for useful paths, line references, likely entry points, and remaining uncertainty.
- Reuse subagent findings as trusted prefetch; read extra files only where the next answer or edit depends on exact code details.

## Avoid

- Workspace-wide semantic queries when a narrower path is available.
- Dumping huge directory trees without depth limits/excludes.
