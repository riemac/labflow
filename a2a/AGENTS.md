# labflow — Unified A2A 1.0 Workbench Transport Layer

Read [../AGENTS.md](../AGENTS.md) for repository conventions. This directory owns the cross-workbench **Agent2Agent (A2A 1.0) transport, session-addressing, and interrupt layer** for Labflow.

## Architectural Boundary (Pure Primitives, Zero Policy)

- **Strict 1:1 A2A 1.0 mapping**:
  - **A2A `Agent`** = Workbench application (`antigravity` permanently online at `http://127.0.0.1:7778`; `codex` permanently online at `http://127.0.0.1:7779`). Neither endpoint goes offline when a desktop GUI restarts.
  - **A2A `contextId`** = Concrete GUI conversation/session (`conversation_id` in Antigravity App `conversation_summaries.db`; `thread_id` in Codex Desktop `session_index.jsonl` / `sessions/*.jsonl`), addressable by UUID, conversation title substring, `latest`, or `new` (Codex).
  - **A2A `Task` (`taskId`)** = Single request-reply exchange (`TASK_STATE_SUBMITTED` → `TASK_STATE_WORKING` → `TASK_STATE_COMPLETED` with `Artifact` reply).
- **Zero hidden fallback policies**: Messages addressed to an Antigravity App session stay strictly inside that `conversation_id`'s isolated mailbox and never silently invoke `agy` CLI to clone/fork the thread. If the target GUI tab has not armed `wait-irq`, the task deterministically remains `TASK_STATE_WORKING` in that session's inbox and emits a desktop notification.
- **Unified Codex hot/cold/new state machine**:
  - `session="new"`: starts a thread via `codex app-server --stdio` with `Codex Desktop` client identity (`source="vscode"`) and drives the initial turn to `turn/completed` so the rollout file is flushed to disk and visible in Codex Desktop's sidebar.
  - Existing session (cold/dormant): `thread/resume` succeeds on `app-server --stdio` and drives `turn/start` to `turn/completed` without `<turn_aborted>` disconnects.
  - Existing session (hot/open in Codex Desktop): `thread/resume` detects `already has an active writer` in `<50ms` and dispatches via native `codex queue --thread <UUID>`, waking the open Codex Desktop GUI live.

## Tracked Vs. Host-Local State

- **Tracked in Git (`a2a/`)**: `labflow_a2a/` (`config.py`, `sessions.py`, `codex_driver.py`, `coordinator.py`, `http_server.py`, `mcp_server.py`, `irq.py`, `cli.py`), `install.sh`, `doctor.sh`, `README.md`, `AGENTS.md`.
- **Host-local only (never commit)**: `~/.local/bin/a2a`, `~/.local/bin/labflow-a2a`, `~/.local/share/labflow-a2a/`, `~/.local/state/labflow-a2a/` (persisted tasks and per-session `armed.json` / `irq.json`), `~/.config/systemd/user/labflow-a2a.service`, and host config backups (`*.bak-*`).

## Validation

```bash
bash -n a2a/install.sh a2a/doctor.sh
python3 -m py_compile a2a/labflow_a2a/*.py
./a2a/install.sh
./a2a/doctor.sh --e2e
```
