---
name: self-update
description: Update the Labflow Codex plugin's skills, dedicated workers, MCP configuration, metadata, or reload helper. Keep host-specific orchestration separate from shared research dossier contracts.
---

# Update Labflow For Codex

Edit the source repository at `/home/hac/labflow`, following its applicable `AGENTS.md` files. The user request defines the authorized scope; do not require another confirmation for already-approved migration or cleanup. Explain consequential choices that remain unresolved.

## Source Surfaces

- `codex/skills/`: independent ability instructions, references, and portable helpers.
- `codex/agents/*.toml`: dedicated asynchronous worker definitions.
- `codex/.mcp.json`: evidence tools.
- `codex/.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json`: metadata and discovery.

Keep `SKILL.md` files concise and operational. Put format templates and checklists under `references/`, deterministic logic and tests under `scripts/`, and reusable figures/assets under `assets/`.

## Reload

Run the reload helper after modifying skills, worker definitions, manifests, or MCP configuration:

```bash
/home/hac/labflow/codex/skills/self-update/scripts/reload_labflow_plugin.sh
```

## Validate And Reload

1. Read the target and relevant callers before editing; preserve unrelated worktree changes and user-owned configuration.
2. Validate changed skills with the installed skill validator, JSON/TOML with their parsers, and shell scripts with `bash -n`. Run affected helper tests and bounded real worker/PDF checks when the orchestration or evidence behavior changes.
3. Review the diff and follow `git-task-flow` for recovery and user-validated semantic closure. Do not stage all files in a dirty worktree.
4. Refresh the installed plugin when needed:

```bash
/home/hac/labflow/codex/skills/self-update/scripts/reload_labflow_plugin.sh
```

Set `LABFLOW_CODEX_BIN` to the desired Codex executable when the App and shell versions differ. The helper refreshes the local marketplace, reinstalls the plugin, resolves the newest cache version containing the reviewer skills, and installs managed regular copies of the four tracked workers (`learning-worker`, `literature-worker`, `paper-editor`, and `paper-reviewer`) into `CODEX_HOME/agents`, preserving user-owned or modified managed files via a checksum ledger. Reviewer skill paths are injected and validated only for `paper-reviewer`; `paper-editor` retains access to the author-side `paper-writing` skill before any target is changed.

Source edits and installed-session behavior are distinct. Start a new session to load the complete refreshed role and skill catalog. Report what was actually tested, remaining runtime limitations, and whether reload was performed; do not claim a migration is behaviorally validated from frontmatter checks alone. Role fields such as disabled skills, memory settings, and `project_doc_max_bytes` are defense layers rather than proof of context isolation: for a blind reviewer, validate from a clean coordinator root with project-document and memory injection disabled where supported, an independent no-history child, and the child's actual startup context. Audit injected content rather than treating every `AGENTS.md` header or generic user collaboration rule as project evidence; generic host rules may remain. If manuscript/project-specific author material was injected, discard that instance's judgment and restart cleanly.

The verified reviewer smoke on App CLI 0.153.4 used an independent `/tmp` cwd, root `-c project_doc_max_bytes=0 -c memories.use_memories=false -c memories.generate_memories=false -c features.memories=false`, and a native `paper-reviewer` spawn with `agent_type=paper-reviewer` and `fork_turns=none`. Audit the actual child startup: generic global rules may remain when they contain no manuscript evidence, while project-specific instructions, memory, author material, and the two author-side skills must be absent. For resubmission, keep the same coordinator and follow up the original reviewer handle after stating the phase allowance; do not silently replace it. When CLI MCP PDF operations require approval, the verified fallback is local extraction/rendering with actual page-image inspection. Record this as host-specific evidence and adapt the command surface to the host instead of adding a universal launcher.

When manuscript/figure review behavior changes, validate the complete author-to-reviewer loop as well as installation. Use two independent focused reviewers of the same fixed PDF, actual page-image inspection, per-stream replies, and same-handle verification on a bounded revision fixture. Keep expected defects, external critiques and author notes outside blind inputs. Inspect what the reviewers noticed and whether they recognize repaired figures; successful image access and static configuration checks do not prove aesthetic judgment. Recheck the installed managed role after a cache/version refresh, since refreshing the plugin alone does not update a separate global worker copy.
