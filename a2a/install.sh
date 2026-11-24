#!/usr/bin/env bash
# Idempotent installer for the Labflow A2A 1.0 interoperability layer.
# Installs official a2a CLI + a2abridge into ~/.local/bin, configures the
# local discovery daemon (with Linux systemd --user log fix), and surgically
# registers the "a2a" MCP server into host configs with automatic backups.

set -euo pipefail

A2A_CLI_VERSION="${A2A_CLI_VERSION:-0.5.0}"
A2ABRIDGE_VERSION="${A2ABRIDGE_VERSION:-4.0.3}"
DIRECTORY_ADDR="${A2A_DIRECTORY_ADDR:-127.0.0.1:7777}"
DIRECTORY_URL="http://${DIRECTORY_ADDR}"
BIN_DIR="${HOME}/.local/bin"

DRY_RUN=0
FORCE=0
SKIP_SERVICE=0
WITH_CLAUDE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --skip-service) SKIP_SERVICE=1 ;;
    --with-claude) WITH_CLAUDE=1 ;;
    -h|--help)
      sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
      echo "Usage: $0 [--dry-run] [--force] [--skip-service] [--with-claude]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
  shift
done

# Resolve OS/arch tuple matching GitHub release asset naming.
UNAME_S="$(uname -s | tr '[:upper:]' '[:lower:]')"
UNAME_M="$(uname -m)"
case "$UNAME_M" in
  x86_64|amd64) ARCH="amd64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  *)
    echo "Unsupported architecture: $UNAME_M" >&2
    exit 1
    ;;
esac

case "$UNAME_S" in
  linux|darwin) OS="$UNAME_S" ;;
  *)
    echo "Unsupported OS: $UNAME_S" >&2
    exit 1
    ;;
esac

log() { printf '[labflow/a2a] %s\n' "$*"; }

install_tarball_binary() {
  local bin_name="$1"
  local expected_ver="$2"
  local url="$3"
  local target="${BIN_DIR}/${bin_name}"

  if [[ "$FORCE" -eq 0 && -x "$target" ]]; then
    local current=""
    current="$("$target" version 2>/dev/null || "$target" --version 2>/dev/null || true)"
    if [[ "$current" == *"$expected_ver"* ]]; then
      log "OK: ${bin_name} ${expected_ver} already installed at ${target}"
      return 0
    fi
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    log "[dry-run] would download ${url} -> ${target}"
    return 0
  fi

  mkdir -p "$BIN_DIR"
  local tmpdir
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' RETURN
  log "Downloading ${bin_name} ${expected_ver} (${OS}/${ARCH})..."
  curl -fsSL "$url" -o "${tmpdir}/pkg.tar.gz"
  tar -xzf "${tmpdir}/pkg.tar.gz" -C "$tmpdir"
  local extracted
  extracted="$(find "$tmpdir" -maxdepth 3 -type f -name "$bin_name" | head -n 1)"
  if [[ -z "$extracted" ]]; then
    echo "Failed to locate '${bin_name}' inside archive from ${url}" >&2
    exit 1
  fi
  install -m 0755 "$extracted" "$target"
  log "Installed ${bin_name} -> ${target}"
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
A2A_URL="https://github.com/a2aproject/a2a-cli/releases/download/v${A2A_CLI_VERSION}/a2a_${A2A_CLI_VERSION}_${OS}_${ARCH}.tar.gz"
BRIDGE_URL="https://github.com/vbcherepanov/a2abridge/releases/download/v${A2ABRIDGE_VERSION}/a2abridge_${A2ABRIDGE_VERSION}_${OS}_${ARCH}.tar.gz"

install_tarball_binary "a2a" "$A2A_CLI_VERSION" "$A2A_URL"
install_tarball_binary "a2abridge" "$A2ABRIDGE_VERSION" "$BRIDGE_URL"

# Install single-threaded MCP wrapper (prevents Linux PR_SET_PDEATHSIG kills under Tokio hosts like Codex Desktop).
WRAPPER_SRC="${SCRIPT_DIR}/a2abridge-mcp.sh"
WRAPPER_DST="${BIN_DIR}/a2abridge-mcp"
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "[dry-run] would install ${WRAPPER_SRC} -> ${WRAPPER_DST}"
else
  install -m 0755 "$WRAPPER_SRC" "$WRAPPER_DST"
  log "Installed MCP wrapper -> ${WRAPPER_DST}"
fi

# Install POSIX sh inbound hook (auto-wakes live Codex Desktop sessions via native `codex queue`).
HOOK_SRC="${SCRIPT_DIR}/on-inbound.sh"
HOOK_DIR="${HOME}/.a2abridge/hooks"
HOOK_DST="${HOOK_DIR}/on-inbound.sh"
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "[dry-run] would install ${HOOK_SRC} -> ${HOOK_DST}"
else
  mkdir -p "$HOOK_DIR"
  install -m 0755 "$HOOK_SRC" "$HOOK_DST"
  log "Installed A2A inbound hook -> ${HOOK_DST}"
fi

# Configure and start the local A2A 1.0 discovery daemon.
if [[ "$SKIP_SERVICE" -eq 0 ]]; then
  if [[ "$OS" == "linux" ]]; then
    UNIT_DIR="${HOME}/.config/systemd/user"
    UNIT_FILE="${UNIT_DIR}/a2abridge-directory.service"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      log "[dry-run] would write user systemd unit ${UNIT_FILE} (journal logging, default.target) and restart"
    else
      mkdir -p "$UNIT_DIR"
      # Upstream v4.0.3 writes StandardOutput=file:/var/log/... which fails under non-root systemd --user.
      UNIT_TMP="$(mktemp)"
      cat > "$UNIT_TMP" <<EOF
[Unit]
Description=Local A2A 1.0 discovery service for AI coding agents.
ConditionFileIsExecutable=${BIN_DIR}/a2abridge

[Service]
ExecStart=${BIN_DIR}/a2abridge service run --addr ${DIRECTORY_ADDR}
StandardOutput=journal
StandardError=journal
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF
      if [[ -f "$UNIT_FILE" ]] && cmp -s "$UNIT_TMP" "$UNIT_FILE" && systemctl --user is-active --quiet a2abridge-directory.service; then
        rm -f "$UNIT_TMP"
        log "OK: systemd --user service a2abridge-directory already up to date and active (${DIRECTORY_URL})"
      else
        mv "$UNIT_TMP" "$UNIT_FILE"
        systemctl --user daemon-reload
        systemctl --user enable --now a2abridge-directory.service
        systemctl --user restart a2abridge-directory.service
        log "Started systemd --user service a2abridge-directory (${DIRECTORY_URL})"
      fi
    fi
  elif [[ "$OS" == "darwin" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      log "[dry-run] would run ${BIN_DIR}/a2abridge service install"
    else
      "${BIN_DIR}/a2abridge" service install
      log "Installed macOS launchd service a2abridge-directory"
    fi
  fi
fi

# Surgically register the "a2a" MCP server in existing host configs without altering other settings.
MCP_CMD="${BIN_DIR}/a2abridge-mcp"
if [[ "$OS" == "darwin" ]]; then
  MCP_CMD="${BIN_DIR}/a2abridge"
fi
python3 - "$MCP_CMD" "$BIN_DIR/a2abridge" "$DIRECTORY_URL" "$DRY_RUN" "$WITH_CLAUDE" <<'EOF'
import datetime, json, pathlib, re, shutil, sys, tomllib

mcp_cmd, raw_bridge_bin, directory_url, dry_run_s, with_claude_s = sys.argv[1:6]
dry_run = dry_run_s == "1"
with_claude = with_claude_s == "1"
home = pathlib.Path.home()
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def backup_file(path: pathlib.Path):
    bak = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, bak)
    return bak

def patch_json_mcp(path: pathlib.Path, peer_name: str, include_disabled: bool):
    if not path.exists():
        print(f"[labflow/a2a] SKIP: {path} not present on this host")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    servers = data.setdefault("mcpServers", {})
    desired = {
        "command": mcp_cmd,
        "args": ["bridge", "-name", peer_name, "-directory", directory_url],
    }
    if include_disabled:
        desired["disabled"] = False
    if servers.get("a2a") == desired:
        print(f"[labflow/a2a] OK: {path} already has matching 'a2a' MCP entry")
        return
    if dry_run:
        print(f"[labflow/a2a] [dry-run] would register 'a2a' ({peer_name}) in {path}")
        return
    bak = backup_file(path)
    servers["a2a"] = desired
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    print(f"[labflow/a2a] Updated {path} (backup: {bak.name})")

def patch_codex_toml(path: pathlib.Path):
    if not path.exists():
        print(f"[labflow/a2a] SKIP: {path} not present on this host")
        return
    raw = path.read_text(encoding="utf-8")
    parsed = tomllib.loads(raw)
    existing = parsed.get("mcp_servers", {}).get("a2a")
    desired_args = ["bridge", "-name", "codex", "-directory", directory_url]
    if existing and existing.get("command") == mcp_cmd and existing.get("args") == desired_args:
        print(f"[labflow/a2a] OK: {path} already has matching [mcp_servers.a2a]")
        return
    # Upgrade in-place if previously registered by labflow/a2a with raw a2abridge binary
    if existing and existing.get("command") == raw_bridge_bin and existing.get("args") == desired_args:
        if dry_run:
            print(f"[labflow/a2a] [dry-run] would upgrade [mcp_servers.a2a] command to {mcp_cmd} in {path}")
            return
        bak = backup_file(path)
        updated = re.sub(
            r'(\[mcp_servers\.a2a\]\s*\ncommand\s*=\s*")' + re.escape(raw_bridge_bin) + r'"',
            r'\1' + mcp_cmd + '"',
            raw,
            count=1,
        )
        tomllib.loads(updated)
        path.write_text(updated, encoding="utf-8")
        print(f"[labflow/a2a] Upgraded [mcp_servers.a2a] command to {mcp_cmd} in {path} (backup: {bak.name})")
        return
    if existing is not None:
        print(f"[labflow/a2a] WARN: {path} already defines [mcp_servers.a2a] with custom settings; leaving untouched")
        return
    if dry_run:
        print(f"[labflow/a2a] [dry-run] would append [mcp_servers.a2a] to {path}")
        return
    bak = backup_file(path)
    addition = (
        "\n[mcp_servers.a2a]\n"
        f'command = "{mcp_cmd}"\n'
        f'args = ["bridge", "-name", "codex", "-directory", "{directory_url}"]\n'
    )
    path.write_text(raw.rstrip("\n") + "\n" + addition, encoding="utf-8")
    tomllib.loads(path.read_text(encoding="utf-8"))
    print(f"[labflow/a2a] Appended [mcp_servers.a2a] to {path} (backup: {bak.name})")

patch_json_mcp(home / ".gemini/antigravity/mcp_config.json", "antigravity", include_disabled=True)
patch_json_mcp(home / ".gemini/config/mcp_config.json", "antigravity", include_disabled=True)
patch_codex_toml(home / ".codex/config.toml")

if with_claude:
    patch_json_mcp(home / ".claude.json", "claude-code", include_disabled=False)
EOF

log "Done. Run ./a2a/doctor.sh (or ./a2a/doctor.sh --e2e) to verify."
