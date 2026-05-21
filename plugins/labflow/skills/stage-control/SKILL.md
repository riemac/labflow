---
name: stage-control
description: Lightweight control surface for Labflow stage-driven development. Use when the user asks to enable, inspect, pass, cancel, or troubleshoot Labflow stage state and hooks.
---

# Labflow Stage Control

Stage control is a thin runtime for research workflows that need temporary stage awareness without heavy orchestration.

## Commands

- `$stage-idea-refine`: enter the research idea refinement stage.
- `$stage-goal-clarify`: enter the goal and acceptance-criteria clarification stage.
- `$stage-pass`: mark the current stage as passed.
- `$stage-cancel`: cancel the current stage.
- `$stage-status`: report current stage state.

Stage entry requires the `$` prefix. Mentioning `stage-idea-refine` in prose or a file path must not activate runtime state.

The authoritative state is stored under the active project and scoped by Codex session:

```text
.codex/labflow-stage/sessions/<session-id>.json
```

A legacy `.codex/labflow-stage/state.json` may exist from older versions, but current hook events with `session_id` do not read it.

## Runtime Behavior

- `UserPromptSubmit` injects model-visible context only for the current Codex session while a stage is active.
- `Stop` only clears state when the assistant emits a standalone `$stage-pass` or `$stage-cancel` line.
- `Stop` does not push an extra continuation turn by default.
- When a stage starts, the hook best-effort opens a Ghostty `+new-window` HUD. If Ghostty is unavailable, it silently skips the HUD. Closing the HUD window does not finish the stage.

## Hook Enablement

Plugin-bundled hooks require Codex config opt-in:

```toml
[features]
plugin_hooks = true
```

Check or update the local config with:

```bash
python3 <plugin-root>/skills/stage-control/scripts/check_stage_hooks.py --check
python3 <plugin-root>/skills/stage-control/scripts/check_stage_hooks.py --write
```

Use `--write` only when the user explicitly wants Labflow to update `~/.codex/config.toml`.

## Agent Contract

When a stage is active, keep the conversation inside that stage unless the user exits it. If the stage is clearly complete, either ask the user to send `$stage-pass` or include a standalone `$stage-pass` line.

Do not treat stage control as a replacement for Codex native Plan Mode or normal implementation.
