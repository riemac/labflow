# Changelog

## 0.10.2 - 2026-07-15

- Added cross-platform Background-First Prefetch and subagent-continuity guidance: launch delegated work asynchronously when available, continue non-overlapping main-agent work, wait only at dependency barriers, reuse related workers, keep write ownership disjoint, and verify critical facts before final synthesis.

## 0.10.1 - 2026-07-13

- Added OpenCode and Codex subagent-continuity guidance: use workers primarily for read-heavy work, resume the same bounded evidence chain when useful, and keep implementation, user context, and final synthesis with the primary agent.

## 0.10.0 - 2026-07-12

- Decoupled scholarly retrieval from the `literature-forensics` skill: the skill now consumes the independently installed `litnav` CLI and retains only a standard-library research-directory helper.
- Split literature dossiers into researcher-facing `overview.md`, curated `MAP.md`, and complete `topics/*.md` reports versus hidden `.research/` audit, PDF, bibliography, and task state.
- Added explicit `fast`, `normal`, and `deep` literature-worker profiles with research-language propagation and bounded new-paper/primary-read limits.
- Fixed plugin agent loading so YAML frontmatter configures model, variant, permissions, and prompt separately; `literature-worker` now resolves to `gmn/gpt-5.6-terra` with `xhigh` reasoning.

## 0.9.0 - 2026-07-10

- Added the OpenCode-only `literature-forensics` skill for research-question framing, prior-art verification, citation snowballing, evidence grading, novelty-boundary analysis, and durable human-first research dossiers.
- Added a local Python CLI that searches and reconciles arXiv, OpenAlex, Semantic Scholar, and Crossref metadata; maintains a concurrent SQLite evidence cache; traverses bounded citation graphs; downloads verified PDFs; exports BibTeX; and persists resumable worker state.
- Added the hidden `literature-worker` subagent for bounded topic-lane research while keeping the primary agent responsible for key-paper verification, visual evidence, synthesis, and scientific claims.
- Upgraded the bilingual `pdf-read` guidance to the pdf-reader MCP v3 evidence workflow with document maps, targeted search, page rendering, region crops, optional OCR, and visual source verification.

## 0.8.0 - 2026-07-10

- Replaced the legacy `/imagegen` command with a plugin-registered `imagegen` tool that returns structured output directly to OpenCode agents.
- Added independent, layered image-generation configuration with Images API and Responses API support, local secret overrides, environment overrides, and safe workspace-relative output paths.
- Added plugin dependency installation and legacy command cleanup to the OpenCode installer, and removed the redundant vision-only subagent now that the active model stack handles images natively.

## 0.7.0 - 2026-07-01

- Added `labflow-paper`, an OpenCode primary agent for research paper preparation, writing guidance, claim/evidence alignment, reviewer-style critique, polishing, and submission readiness.
- Registered `labflow-paper` in the OpenCode plugin and updated install messaging so the paper agent appears alongside `labflow-develop` and `labflow-plan` after restart.
- Switched OpenCode agent prompt loading to explicit startup-time file reads so plugin-registered agents receive their full prompt bodies reliably.
- Refreshed OpenCode guidance around Plan Mode, distributed prompting conflicts, tool availability, codebase research, external research routing, and annotation cleanup.
- Removed the legacy `plugins/labflow/benchmark/test_rag.md` RAG benchmark note from the active tracked surface.

## 0.6.1 - 2026-06-25

- Bundled DeepWiki as a labflow Codex MCP server for public GitHub repository code maps, source location, and implementation explanations.
- Updated Codex and OpenCode `external-research` routing to use DeepWiki before lower-level GitHub/source tooling when the task is public repository structure or source understanding.

## 0.6.0 - 2026-06-14

- Added `labflow-plan`, a read-only OpenCode primary agent that adapts Codex Plan Mode into an explore-first, question-driven workflow ending in a `<proposed_plan>` block.
- Updated OpenCode integration docs and install messaging to route structured planning through `labflow-plan`, implementation through `build`, and nonlinear R&D/scaffolding through `labflow-develop`.
- Documented the `self-update` evidence path for checking OpenCode configuration and internals via ctx7 first, then GitHub source for the installed version.

## 0.5.1 - 2026-06-14

- Tightened `codebase-research` so agents must load/read the `ccc` skill before semantic code retrieval, and synchronized the Codex/OpenCode English and Chinese skill copies around `ccc` as the active local semantic search tool.

## 0.5.0 - 2026-06-08

- Added OpenCode integration: plugin-based architecture with `labflow.ts` config hook injecting global rules, primary agent (`labflow-develop` merges idea-refine + design-scaffold), `vision` subagent, and 10 adapted ability skills.
- Split `AGENTS.md` into thin cross-platform entry + `AGENTS_Codex.md` + `AGENTS_Opencode.md`.
- Added `neat-freak` skill (end-of-session AGENTS.md/docs knowledge cleanup) for both Codex and OpenCode.
- Rewrote `pdf-read` skill with `pdf-reader` MCP as primary tool and image reading emphasis.
- Added `<tools>` CLI reference section to `stage-AGENTS.md` and `labflow-rules.md`.
- Migrated `stage-AGENTS.md` global rules (`feedback-and-discussion`, `distributed-prompting`) into OpenCode's additive `instructions` mechanism.
- Removed filler routing lines from `deep-research` and `external-research`.
- Updated `.gitignore` with labflow workspace file.

## 0.4.1 - 2026-06-02

- Reworked `codebase-research` around a provider-neutral local retrieval evidence chain: semantic/code-RAG recall, `tree`/`fd`/`rg` shell narrowing, and key-file reading.
- Added a Chinese companion `SKILL_CN.md` for `codebase-research`.
- Removed the bundled Augment/Auggie MCP server config and updated project prompts/docs to avoid treating Augment as the default local semantic search provider.
- Added IsaacLab RAG benchmark questions while ignoring generated benchmark result reports.
