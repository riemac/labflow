# Labflow Unified A2A 1.0 Workbench Layer

`a2a/` provides a single, zero-dependency, host-portable [A2A 1.0](https://a2a-protocol.org/latest/) transport service (`labflow-a2a`) connecting **Antigravity App** (`127.0.0.1:7778`) and **Codex Desktop App** (`127.0.0.1:7779`) at the **individual conversation/session level**, strictly decoupled from upper-level workflow skills.

## Core Design

- **Always-On Endpoints**: `labflow-a2a.service` keeps `antigravity` (`:7778`) and `codex` (`:7779`) permanently online across GUI restarts and registers both in the official `a2a` CLI contact book.
- **Session-Level Addressing (`contextId`)**: List and target specific conversations by **UUID**, **conversation title**, `latest`, or `new` (Codex).
- **Hot, Cold, and New Codex Sessions**: Open Codex Desktop chats wake live via `codex queue`; closed/restarted chats automatically revive from disk with full history via `codex app-server` `thread/resume` and stay visible in Codex Desktop's sidebar.
- **Race-Free Antigravity GUI Interrupt (`wait-irq`)**: Arming `labflow-a2a wait-irq` in an Antigravity tab blocks on Linux `inotify` at **0% CPU / 0 tokens** and wakes that exact GUI tab in `<1ms` when Codex messages it. Never silently clones App sessions into `agy` CLI.

## Quickstart (New Host Deployment)

```bash
./a2a/install.sh
./a2a/doctor.sh --e2e
```

## MCP Primitives (Shared Across Both Workbenches)

| Tool | Purpose |
| :--- | :--- |
| `a2a_list_agents` | Check online health of `antigravity` (`:7778`) and `codex` (`:7779`) |
| `a2a_list_sessions` | List GUI conversations (`session_id`, `title`, `cwd`, `irq_armed`, `pending_inbox_count`) |
| `a2a_send` | Send message to `agent` + `session` (`<UUID \| title \| latest \| new>`), blocking or async |
| `a2a_get_task` | Poll task status and reply artifacts by `task_id` |
| `a2a_inbox` | Read pending tasks isolated to the current GUI session |
| `a2a_reply` | Attach reply artifact, mark `TASK_STATE_COMPLETED`, and immediately unblock sender |

## CLI & Interrupt Usage

```bash
# Inspect Agent Cards or send messages via official a2a CLI
a2a card get codex
a2a card get antigravity
a2a send -a codex --context-id "Respond to greeting" "Check this hypothesis"

# Arm zero-CPU interrupt wakeup inside an active Antigravity App tab
~/.local/bin/labflow-a2a wait-irq
```
