---
name: external-research
description: External research orchestration skill. Use for third-party libraries/APIs, official docs, public GitHub repository code understanding, upstream source, version migrations, papers/PDFs, GitHub releases/issues/PRs, and high-noise/low-signal deep research. Default to ctx7 CLI / find-docs for docs and APIs; default to DeepWiki MCP for public GitHub repository structure/source explanations when available; use gh CLI only when GitHub-native evidence is needed; strongly delegate high-noise research to the built-in scout subagent. Do not use for local codebase architecture or symbol research.
---

# External Research

This skill is lightweight orchestration only.

## Default Route

- Library/API/official-doc/config/migration: use `find-docs` skill / ctx7 CLI. Do not jump to `gh` just because the target library is hosted on GitHub.
- Public GitHub repository codemaps, source location, and cross-file implementation explanations: use DeepWiki MCP before `ctx7` when available. DeepWiki is good for quickly locating relevant source and understanding implementation shape, but it does not replace full source reads, exact line evidence, official docs, or issue/PR/release evidence; add local source, GitHub raw, `gh`, or official docs for those cases. Do not use DeepWiki for private repositories; use local source or an authorized data source instead.
- Only use `gh` CLI when the question itself needs GitHub evidence: release/tag dates, issues/PRs/discussions, upstream source implementation, commit diffs, repo metadata, or npm/release status checks.
- Papers, technical reports, PDF specs, remote PDFs: use `pdf-read` / pdf-reader.
- ctx7 does not cover it, the official site is not on GitHub, or cross-source material is needed: then use web search/browser.

Decision order: first ask "Is this a docs/API usage question?" If yes, use ctx7 first. Then ask "Is this public GitHub repository structure/source understanding?" If yes, use DeepWiki first. Then ask "Does the answer depend on GitHub facts or auditable source evidence?" If yes, add `gh` / raw source. Do not expand the tool surface just for formal completeness.

## Delegate

For high-noise, low-signal, multi-hop external research, strongly consider delegating to the built-in `scout` subagent in parallel. The goal is to absorb retrieval noise in the subagent's context, keeping the main context clean of long webpages, issue threads, partial hits, and dead-end docs.

Signals:

- A single ctx7 / DeepWiki / web / gh query is unlikely to answer directly.
- Many search results exist, but very little decisive evidence.
- Multiple issues, PRs, discussions, release notes, or long docs must be scanned to find the key fact.
- Research directions are independent enough to split across parallel subagents.
- The main agent still needs to implement or design afterward and should not carry retrieval noise.

## Keep It Small

- Keep only implementation-relevant facts: decisive source, URL/repo path, version/date, and key uncertainty.
- Leave broad retrieval, trial-and-error, and dead ends in the subagent context.
- Do not dump raw documents.
- Do not force every tool just for "completeness."
