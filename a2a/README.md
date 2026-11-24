# Labflow A2A 1.0 Interoperability Layer

`a2a/` provides a reproducible, host-portable [A2A 1.0](https://a2a-protocol.org/latest/) communication backbone connecting local AI coding harnesses (**Antigravity App / CLI**, **Codex Desktop / CLI**, and optionally **Claude Code** and **OpenCode**) without reinventing proprietary bridges or coupling transport logic into upper-level skills.

## Components

- **Official `a2a` CLI** ([`a2aproject/a2a-cli`](https://github.com/a2aproject/a2a-cli), Apache-2.0): standard command-line client for Agent Card discovery (`a2a card get`), message sending, streaming, and interacting with external A2A 1.0 peers.
- **`a2abridge`** ([`vbcherepanov/a2abridge`](https://github.com/vbcherepanov/a2abridge), MIT, built on `a2a-go`): single Go binary providing the local A2A 1.0 discovery directory (`127.0.0.1:7777`), per-session MCP stdio bridge (`a2a_whoami`, `a2a_list_agents`, `a2a_send_message`, `a2a_send_streaming`, `a2a_get_task`, `a2a_cancel_task`, `a2a_inbox`, `a2a_complete_task`), and optional detached workers.

## Quickstart (New Host Deployment)

From the repository root on Linux (`x86_64` / `arm64`) or macOS:

```bash
./a2a/install.sh
./a2a/doctor.sh --e2e
```

Optional flags:

- `--dry-run`: preview planned binary downloads, service actions, and MCP patches without writing files.
- `--force`: re-download pinned binary versions even if already installed.
- `--with-claude`: also register the `a2a` MCP entry in `~/.claude.json` (if present).
- `--with-opencode`: print or prepare OpenCode MCP guidance without overwriting managed OpenCode profiles.
- `--skip-service`: install binaries and MCP entries without touching the local directory daemon.

Version pins can be overridden via environment variables:

```bash
A2A_CLI_VERSION=0.5.0 A2ABRIDGE_VERSION=4.0.3 ./a2a/install.sh
```

## Day-to-Day Usage

1. **Live Workbench Collaboration (Antigravity App ↔ Codex Desktop App)**: After running `./a2a/install.sh`, reload or open a fresh session in both apps. Each open session automatically registers itself as a standard A2A 1.0 peer under `http://127.0.0.1:7777`. Call `a2a_list_agents` to discover live peers, `a2a_send_message` to dispatch work, and `a2a_inbox` / `a2a_complete_task` to read and reply.
2. **CLI Inspection & External Peers**:

```bash
curl -s http://127.0.0.1:7777/agents | python3 -m json.tool
a2a card get http://127.0.0.1:<peer-port>
```

3. **Rollback**: Every modified host config (`~/.gemini/antigravity/mcp_config.json`, `~/.gemini/config/mcp_config.json`, `~/.codex/config.toml`) is backed up as `<file>.bak-<YYYYMMDD-HHMMSS>` before patching. Restore the backup and run `systemctl --user disable --now a2abridge-directory.service` (Linux) or `a2abridge service uninstall` (macOS) to cleanly revert.
