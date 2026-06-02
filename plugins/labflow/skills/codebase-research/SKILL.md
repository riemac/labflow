---
name: codebase-research
description: Local codebase research skill for architecture tracing, symbol discovery, call-chain analysis, similar implementation lookup, config registration paths, and cross-file data-flow understanding. Use local semantic retrieval, shell search, and key-file reading; do not use for external docs, papers, or third-party API research.
---

# Codebase Research

Use only for **local codebase research**. For external docs, upstream source, releases, GitHub issues/PRs, papers, or third-party APIs, use `external-research`.

## Default Loop

Use max parallelism whenever branches are independent.

1. **Semantic retrieval**: use the current local semantic/code-RAG tool as a thin, replaceable entry point. Query one concept at a time. Always scope to the narrowest defensible repo/subproject/module path; re-scope deeper as evidence appears. Follow the active tool's own skill/docs for query style.
2. **Shell narrowing**: use `tree` for structure, `fd` for file discovery, and `rg` for symbols/config keys/strings. Always use depth limits and excludes for caches, dependencies, generated files, logs, outputs, and data.
3. **Read key files**: verify behavior in entry points, definitions, registration sites, one caller/callee layer, similar implementations, and relevant tests/examples. If key paths are already known, read directly; do not force semantic search.

Example shell probes:

```bash
tree target_dir -L 3 -a -I '.git|__pycache__|.venv|node_modules|dist|build|logs|outputs|.cocoindex_code'
fd 'reward|manager|cfg' target_dir
rg -n "RewardManager|RewTerm|RewardsCfg" target_dir
```

## Subagent Delegation

Keep delegation separate from the default loop. Use it when many independent branches would consume the main context.

- Give each subagent one narrow path scope and one concrete question.
- Ask for paths, line references, uncertainty, and decisive files to read.
- Do not paste subagent output as the final answer.
- The main agent must still read decisive files before making implementation claims.

## Output

Keep results decision-oriented:

- Conclusion: how the local code works.
- Evidence: paths, lines, symbols, config keys, or call chains.
- Reusable pattern: closest existing implementation.
- Implementation impact: likely files/interfaces/configs to change.
- Uncertainty: what was not inspected and why it does not block the current decision.

## Avoid

- Binding this skill to one semantic-search provider.
- Workspace-wide semantic queries when a narrower path is available.
- Treating retrieval or subagent summaries as proof.
- Dumping huge directory trees without depth limits/excludes.
- Writing a broad architecture tour instead of answering the task.
