# labflow — Codex Plugin Development

Read [../AGENTS.md](../AGENTS.md) for repository conventions. Codex uses its native primary agent and Plan Mode. Labflow supplies focused evidence skills and asynchronous workers; it does not ship primary-agent personas, stage switching, lifecycle hooks, or a HUD.

## Surfaces And Ownership

- `.agents/plugins/marketplace.json`: local marketplace entry (pointing to `./codex`).
- `codex/.codex-plugin/plugin.json`: plugin metadata and skill discovery.
- `codex/.mcp.json`: PDF reader and DeepWiki MCP configuration.
- `codex/skills/`: independent research abilities and maintenance support.
- `codex/agents/*.toml`: dedicated worker definitions for learning forensics, literature forensics, author-side paper editing, and independent paper review.

The manifest version tracks the repository `VERSION`, including OpenCode-only patch releases; a version synchronization does not imply a change to Codex agent behavior.

Document, presentation, spreadsheet, PDF production, image generation, and general Deep Research use the host's available skills/tools. `paper-writing` and `scientific-figures` coordinate manuscript and figure decisions without duplicating those native APIs; `external-research` remains a lightweight source-routing ability; `literature-forensics` owns the specialized prior-art investigation contract.

## Shared Research Contracts

Literature and learning dossier layouts, scientific evidence semantics, and portable helpers remain compatible across platforms. Host tool names, worker registration, and lifecycle instructions are platform adapters. Do not change the dossier format merely to encode a Codex worker handle.

The primary owns the user relationship, scientific decisions, central state, and human-facing reports. Workers receive bounded questions and disjoint hidden audit targets. Model and reasoning effort are managed by user configuration. The approved dedicated-worker settings are `gpt-5.6-terra` / `max`; global defaults in the personal `config.toml` select `gpt-5.6-luna` / `max` for native general workers. Do not supply runtime overrides or create a replacement `explorer` role. Start independent workers without full-history inheritance.

Use native asynchronous subagents, continue non-overlapping work, and collect results at dependency boundaries. Reuse the worker for the same evidence chain. A persisted handle is host-specific routing metadata, not a cross-session revival guarantee; recover unavailable workers from permitted dossier artifacts. Learning blind rounds must start without inherited parent history and receive only sealed facts and the complete assignment.

Custom agents are discovered from `.codex/agents/*.toml` or `~/.codex/agents/*.toml`. The reload helper installs managed regular copies of the four tracked TOML definitions (`learning-worker`, `literature-worker`, `paper-editor`, and `paper-reviewer`) into `CODEX_HOME/agents`, resolves versioned cache paths and validates the two excluded author-skill paths only for `paper-reviewer`, and preserves user-owned files. `paper-editor` keeps access to the author-side `paper-writing` skill. Their write boundaries are behavioral contracts, not guarantees of path-level sandbox enforcement; inspect actual output during validation.

## Development And Validation

Work on `/home/hac/labflow` on `main`. Inspect the applicable instruction chain before edits and preserve unrelated local changes.

Validate changed skills with the installed system validator:

```bash
python3 /home/hac/.codex/skills/.system/skill-creator/scripts/quick_validate.py codex/skills/<skill-name>
```

Validate changed JSON with `python3 -m json.tool`, TOML with `tomllib`, and reload shell syntax with `bash -n`. Run the shared helper tests when changing literature/learning/review contracts:

```bash
python3 -m unittest discover -s codex/skills/literature-forensics/scripts -p 'test_*.py'
node --test opencode/tests/learning-forensics.test.mjs
python3 -m unittest discover -s codex/skills/self-update/scripts -p 'test_*.py'
```

Static checks do not validate custom-role discovery, asynchronous continuation, blind-input isolation, or artifact boundaries. Use a bounded local-evidence worker smoke test when changing orchestration; report the actual host and any remaining validation gap. Check PDF text location and vector-page rendering with the exposed MCP tools when changing PDF guidance.

## Reload

```bash
codex/skills/self-update/scripts/reload_labflow_plugin.sh
```

Set `LABFLOW_CODEX_BIN` to a specific installed executable when the App and shell CLI differ. The helper refreshes the local marketplace, reinstalls the plugin cache, and installs all four tracked workers. Start a new Codex session to load the complete updated instruction and role catalog. Preserve user-owned agent files and unrelated configuration.
