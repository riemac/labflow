---
name: external-research
description: External research orchestration skill. For third-party libraries/APIs, official docs, public GitHub repository code understanding, upstream source, version migration, papers/PDFs, GitHub releases/issues/PRs, and high-noise/low-signal deep research. Default to ctx7 CLI / find-docs first; use DeepWiki MCP first for public GitHub repo structure/source explanations when available; gh CLI only when GitHub-native evidence is needed; high-noise branches strongly delegate to the built-in scout subagent.
---

# External Research

Lightweight orchestration only — this skill does not duplicate ctx7 usage docs.

## Default Route

- Library/API/official-doc/config/migration: use `find-docs` skill / ctx7 CLI first. Do not jump to `gh` just because the target library is hosted on GitHub.
- Public GitHub repository codemaps, source location, and cross-file implementation explanations: use the DeepWiki MCP first when available. DeepWiki is good for quickly finding relevant source and understanding implementation shape, but it does not replace full source reads, exact line evidence, official docs, or issue/PR/release evidence; add local source, GitHub raw, `gh`, or official docs for those cases. Do not use DeepWiki for private repositories; use local source or an authorized data source instead.
- Only use `gh` CLI when the question itself needs GitHub evidence: release/tag dates, issues/PRs/discussions, upstream source, commit diffs, repo metadata, or npm/release status checks.
- Papers, technical reports, PDF specs, remote PDFs: use `pdf-read` / pdf-reader.
- ctx7 doesn't cover it, the official site isn't on GitHub, or cross-source material is needed: then web search/browser.

Decision order: is this a docs/API-usage question? -> ctx7 first. Is this public GitHub repo structure/source understanding? -> DeepWiki first. Does the answer need GitHub-native facts or auditable source evidence? -> add `gh` / raw source. Don't expand the tool surface for formality's sake.

## Bootstrap

If ctx7 is needed but the `ctx7` command is missing, run the helper:

```bash
bash <plugin-root>/skills/external-research/scripts/ctx7_bootstrap.sh status --json
bash <plugin-root>/skills/external-research/scripts/ctx7_bootstrap.sh ensure --yes
```

`ensure` only installs/configures `ctx7`, `find-docs`, `context7-cli` — don't treat it as a query interface.

## Delegate

For high-noise, low-signal, multi-hop external research, delegate to the built-in `scout` subagent in parallel. The goal is to absorb retrieval noise in the subagent's context, keeping the main context clean of long webpages, issue threads, partial results, and dead-end docs.

Signals:

- A single ctx7 / web / gh query unlikely to answer directly.
- Many search results, very little decisive evidence.
- Need to dig through multiple issues, PRs, discussions, release notes, or long docs to find key facts.
- Independent research directions that can be split across parallel subagents.
- The main agent still has implementation or design work ahead and shouldn't carry retrieval noise.

## Keep It Small

- Keep only what affects implementation: decisive source, URL/repo path, version/date, and key uncertainty.
- Leave broad retrieval, trial-and-error, and dead ends in the subagent context.
- Don't dump raw documents.
- Don't force every tool just for "completeness."
