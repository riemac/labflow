---
name: codebase-research
description: "Use when an agent needs to inspect a local repository before answering or editing: trace architecture, locate symbols, follow call chains/data flow, find similar implementations, inspect config registration paths, or decide which files to read/change. Use path-scoped ccc semantic retrieval, parallel shell probes, key-file reads, and subagent prefetch. Not for external docs, papers, or third-party API research."
---

## Default Loop

Aim to quickly identify the files and code paths that matter for the current task.

Use max parallelism aggressively: split the task into independent branches, then run semantic retrieval, shell probes, and obvious file reads in parallel. Do not wait for one search to finish before launching other independent searches.

1. **Load `ccc` skill (mandatory)**: when this skill is loaded for local codebase work, immediately load/read the `ccc` skill before issuing semantic queries. `ccc` is the current semantic tool and its skill owns initialization, indexing, search syntax, filtering, pagination, and troubleshooting. Do not rely on remembered `ccc` CLI details.
2. **Semantic retrieval (prefer first)**: use `ccc` as the primary semantic/code-RAG entry point. Query one concept at a time. Always scope to the narrowest defensible repo/subproject/module path; re-scope deeper as evidence appears. Follow the `ccc` skill for query style and lifecycle handling.
3. **Shell narrowing**: use `tree` for structure, `fd` for file discovery (`fdfind` alias; prefer over plain `find`), and `rg` for symbols/config keys/strings (prefer over plain `grep`). Use depth limits and excludes for caches, dependencies, generated files, logs, outputs, and data when useful.
4. **Read key files**: verify behavior in entry points, definitions, registration sites, one caller/callee layer, similar implementations, and relevant tests/examples. If key paths are already known, read directly; do not force semantic search.

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
