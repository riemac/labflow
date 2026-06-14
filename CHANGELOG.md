# Changelog

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
