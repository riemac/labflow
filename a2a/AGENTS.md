# labflow — A2A 1.0 Interoperability Layer

Read [../AGENTS.md](../AGENTS.md) for repository conventions. This directory owns the cross-harness **Agent2Agent (A2A 1.0) transport and deployment layer** for Labflow.

## Architectural Boundary

- **Strict layer decoupling**: `a2a/` is pure transport and discovery infrastructure. It provides standard A2A 1.0 peer addressing, MCP registration, directory lifecycle management, and CLI diagnostics without embedding upper-level research, writing, or coding workflows.
- **No custom UI surface**: Live workbench collaborations (for example Antigravity App ↔ Codex Desktop App) use each harness's native GUI window with `a2abridge` attached as an MCP server (`a2a_list_agents`, `a2a_send_message`, `a2a_get_task`, `a2a_inbox`, `a2a_complete_task`). Headless background delegations run via detached workers or headless A2A peers without cluttering GUI conversation history.
- **Dual entrypoints over one standard wire**:
  - **MCP (`a2abridge bridge`)**: primary structured interface for agents across Antigravity, Codex, Claude Code, and OpenCode, using A2A's asynchronous task state machine (`submitted` → `working` → `completed`) to avoid synchronous MCP call timeouts.
  - **Official CLI (`a2aproject/a2a-cli`)**: standard `a2a` binary for Agent Card inspection (`a2a card get`), streaming debugging, and calling external or remote A2A 1.0 peers.

## Tracked Vs. Host-Local State

- **Tracked in Git (`a2a/`)**: `install.sh`, `doctor.sh`, `a2abridge-mcp.sh`, `on-inbound.sh`, `README.md`, `AGENTS.md`.
- **Host-local only (never commit)**: binaries and installed wrapper under `~/.local/bin/`, runtime directory state and installed hooks under `~/.a2abridge/`, user systemd units under `~/.config/systemd/user/`, host config backups (`*.bak-*`), and optional mTLS federation keys/certificates.

## Ownership And Safety Rules

- `a2a/install.sh` manages host-level MCP registration (`~/.gemini/antigravity/mcp_config.json`, `~/.gemini/config/mcp_config.json`, `~/.codex/config.toml`) rather than hard-coding `a2abridge` into `codex/.mcp.json`, so hosts that have not installed A2A binaries remain unaffected.
- Always back up existing host configuration files before patching and preserve every unrelated setting byte-for-byte.
- On Linux `systemd --user`, `install.sh` writes a clean user unit with `StandardOutput=journal`, `StandardError=journal`, and `WantedBy=default.target` to avoid upstream `a2abridge v4.0.3` attempting to write to root-owned `/var/log/a2abridge-directory.out`.
- On Linux, MCP hosts launch `~/.local/bin/a2abridge-mcp` (installed from `a2a/a2abridge-mcp.sh`) instead of invoking `a2abridge` directly. This keeps a stable single-threaded parent alive so multi-threaded hosts (such as Codex Desktop / Rust Tokio) retiring idle worker threads do not trigger Linux `PR_SET_PDEATHSIG` `SIGTERM` and break active MCP pipes (`Transport closed`).
- `a2a/on-inbound.sh` (installed to `~/.a2abridge/hooks/on-inbound.sh`) MUST remain strict POSIX `sh` because upstream `a2abridge` executes user hooks via `/bin/sh` directly. When an inbound A2A task arrives at a live Codex Desktop session (`app-server` ancestor, excluding headless `codex exec`), the hook resolves the active Codex Desktop thread UUID for the session's `cwd` and invokes native `codex queue --thread <UUID>` (deduplicated by `taskId`, opt-out via `LABFLOW_A2A_AUTO_WAKE=0`) so Codex Desktop wakes up and replies automatically inside its GUI workbench. For Antigravity inbound tasks, it emits a desktop notification via `notify-send` if available.

## Validation

```bash
bash -n a2a/install.sh a2a/doctor.sh a2a/a2abridge-mcp.sh
sh -n a2a/on-inbound.sh
./a2a/doctor.sh
./a2a/doctor.sh --e2e
```
