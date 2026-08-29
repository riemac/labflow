# Changelog

## 1.1.1 - 2026-08-30

- Exposed OpenCode's native GPT-5.6 Sol, Terra, and Luna Fast modes for ChatGPT OAuth while retaining their Standard entries and existing defaults.

## 1.1.0 - 2026-08-30

- Added cross-platform `learning-forensics`, a causal investigation method for supervised, unsupervised, self-supervised, generative, reinforcement-learning, and robotics failures that freezes hypothesis-free casefiles, locates the earliest broken learning link, and prioritizes discriminative probes before formal tuning.
- Added the reusable hidden `learning-worker` for up to eight independent blind lenses, resumable cross-examination, focused external evidence, disjoint audit artifacts, and explicitly bounded ten-minute probe execution while the primary agent retains scientific judgment and human-facing synthesis.
- Added local-only learning case dossiers with dynamic paper-flavor topic reports, sealed case identities, evidence indexes, hidden worker state, isolated probe scaffolds, and a standard-library `init`/`new-case`/`seal-case`/`new-probe`/`validate` helper.
- Added tracked `opencode-pty` integration and global long-process ownership rules so primary agents can launch user-approved formal jobs with exit notifications, focused log recovery, and explicit permission caveats without polling.

## 1.0.2 - 2026-08-17

- Restored native ChatGPT Plus/Pro OAuth for the `openai` provider by removing the Routin Plan endpoint and managed credential injection; relay providers continue to use distinct IDs.
- Limited native OpenAI selection to the GPT-5.6 Sol, Terra, and Luna models and configured each with a 372k context/input budget and 64k output budget.

## 1.0.1 - 2026-08-12

- Added a unified read-only OpenCode `explore-worker` for bounded local and external evidence retrieval with caller-selected `fast`, `normal`, or `deep` scope profiles, `normal` by default, resumable profile changes, timely diminishing-return stops, and user-overridable Luna/xhigh model defaults; disabled the built-in `explore` and `general` workers.
- Rebuilt `neat-freak` as a compact cross-platform governance method for existing root and nested `AGENTS.md` and `README.md` files, including explicit creation and maintenance authorization, a 150-line AGENTS limit, a stable engineering-contract template, and research-oriented human README guidance.
- Tightened shared delegation guidance and the codebase, external, and deep-research routes around one coherent worker per evidence chain, direct reads for known targets, background prefetch, task reuse, and concise evidence returns before worker context growth delays the parent session.
- Made newly initialized literature-forensics dossiers ignore their entire local directory through a dossier-owned `.gitignore`, keeping all research artifacts out of the enclosing Git worktree without changing the host repository's ignore rules.

## 1.0.0 - 2026-08-07

- Moved portable OpenCode defaults, third-party plugin declarations, eight relay providers, and twenty-five model definitions into tracked YAML loaded by the labflow plugin, while reducing the machine-local global config to a generated startup bootstrap.
- Added explicit SOPS + per-device age migration, authorization, backup, idempotency, dependency checks, and doctor workflows; provider credentials now enter request-time secure fetch closures instead of resolved OpenCode config or diagnostic output.
- Added named imagegen profiles and conservative ordered routes, including Lucoo and GMN `gpt-image-2` profiles, retry classification, ambiguous-timeout controls, redacted failures, and rollback-safe staged output commits.
- Added deterministic config, migration, authentication, leakage, fallback, and plugin regression coverage, plus public-repository setup and new-device authorization documentation.

## 0.10.7 - 2026-07-27

- Added explicit `useLatestAttachedImages` support for referring to the most recent image-bearing user message across turns without weakening the strict current-message semantics of `useAttachedImages`.
- Documented current, latest-session, workspace-path, fresh-generation, and correction branches in the imagegen skill's XML/Mermaid workflow, with mutually exclusive one-shot attachment scopes.
- Removed the asymmetric build-only per-turn system marker and restored native OpenCode agent-switching semantics; explicit user reminders or fresh sessions handle residual same-session confusion.
- Strengthened Git Task Flow version closure so accepted VERSION/Changelog releases receive verified `v${VERSION}` tags, with explicit handling for legacy and skipped versions.

## 0.10.6 - 2026-07-25

- Let user-level OpenCode configuration override the bundled `literature-worker` agent definition, including provider and model selection, while retaining its portable defaults for all unspecified fields.

## 0.10.5 - 2026-07-24

- Count only unique papers with a downloaded, verified PDF read at `full` depth, including the main body, method, experiments/results, limitations/discussion, and relevant appendices; title, metadata, abstract, citation, and targeted-page evidence remains uncounted.
- Replace paper-discovery and primary-read budgets with `max_full_papers`, defaulting to `fast: 0`, `normal: 3`, and `deep: 5`; allow fast targeted key-page checks and resume the same task ID across explicit profile assignments in one evidence chain.

## 0.10.4 - 2026-07-22

- Added bounded Responses API reference-image editing for up to four local PNG/JPEG/WebP inputs, including explicit current-message OpenCode image attachments, worktree-safe input snapshots, reference lineage, and request-versus-actual size metadata.
- Extended the imagegen skill with upload editing, local-output iteration, fresh-regeneration branching, preserved iteration history, and at most two autonomous corrections for objective visual constraint failures.
- Added deterministic CLI and mock-provider plugin tests for text-only generation, multi-image edit payloads, attachment lifecycle, API boundaries, output writing, and path safety.

## 0.10.3 - 2026-07-21

- Let image-generation profiles reuse any configured OpenCode provider, with `routin-plan/gpt-5.6-sol` as the bundled Responses API default.
- Refactored `labflow-develop` into a compact nonlinear research-dialogue agent for intent framing, method critique, mathematical explanation, adaptive visualization, and zero-symbol design scaffolds.
- Added a build-only per-turn agent marker so same-session switches do not remain constrained by a previously active primary agent's mode prompt.
- Added OpenCode Desktop LaTeX delimiter guidance, highlighted `labflow-plan` in the agent UI, and tightened parallel codebase-research guidance.
- Corrected file-based plugin update guidance, aligned cross-agent handoffs with the broader Develop role, and standardized Markdown prose as one physical line per paragraph.

## 0.10.2 - 2026-07-15

- Added cross-platform Background-First Prefetch and subagent-continuity guidance: launch delegated work asynchronously when available, continue non-overlapping main-agent work, wait only at dependency barriers, reuse related workers, keep write ownership disjoint, and verify critical facts before final synthesis.

## 0.10.1 - 2026-07-13

- Added OpenCode and Codex subagent-continuity guidance: use workers primarily for read-heavy work, resume the same bounded evidence chain when useful, and keep implementation, user context, and final synthesis with the primary agent.

> Historical tag note: `0.10.1` had no independent VERSION commit; its notes landed together with `0.10.2`, so no `v0.10.1` tag exists.

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
