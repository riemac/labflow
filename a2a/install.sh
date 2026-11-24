#!/usr/bin/env bash
# Idempotent installer for the Labflow Unified Session-Addressable A2A 1.0 Layer (v2.1.0).
#
# Actions:
#   1. Installs official `a2aproject/a2a-cli` (`a2a`) into ~/.local/bin/a2a.
#   2. Retires legacy `a2abridge` service/binaries/hooks if present from v2.0.x.
#   3. Installs `labflow_a2a.py` -> ~/.local/bin/labflow-a2a and starts the
#      user-level `labflow-a2a` daemon (:7778 antigravity, :7779 codex).
#   4. Surgically registers the `a2a` MCP server in Antigravity & Codex configs
#      with timestamped `.bak` backups and zero unintended config mutations.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
A2A_CLI_VERSION="${A2A_CLI_VERSION:-0.5.0}"
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
      sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
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

UNAME_S="$(uname -s | tr '[:upper:]' '[:lower:]')"
UNAME_M="$(uname -m)"
case "$UNAME_M" in
  x86_64|amd64) ARCH="amd64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  *) echo "Unsupported architecture: $UNAME_M" >&2; exit 1 ;;
esac
case "$UNAME_S" in
  linux|darwin) OS="$UNAME_S" ;;
  *) echo "Unsupported OS: $UNAME_S" >&2; exit 1 ;;
esac

log() { printf '[labflow/a2a] %s\n' "$*"; }

# 1. Install official `a2a` CLI
install_a2a_cli() {
  local target="${BIN_DIR}/a2a"
  local url="https://github.com/a2aproject/a2a-cli/releases/download/v${A2A_CLI_VERSION}/a2a_${A2A_CLI_VERSION}_${OS}_${ARCH}.tar.gz"
  if [[ "$FORCE" -eq 0 && -x "$target" ]]; then
    local cur=""
    cur="$("$target" version 2>/dev/null || "$target" --version 2>/dev/null || true)"
    if [[ "$cur" == *"$A2A_CLI_VERSION"* ]]; then
      log "OK: a2a ${A2A_CLI_VERSION} already installed at ${target}"
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
  log "Downloading official a2a ${A2A_CLI_VERSION} (${OS}/${ARCH})..."
  curl -fsSL "$url" -o "${tmpdir}/a2a.tar.gz"
  tar -xzf "${tmpdir}/a2a.tar.gz" -C "$tmpdir"
  local extracted
  extracted="$(find "$tmpdir" -maxdepth 3 -type f -name "a2a" | head -n 1)"
  install -m 0755 "$extracted" "$target"
  log "Installed a2a -> ${target}"
}

install_a2a_cli

# 2. Cleanly retire legacy v2.0.x `a2abridge` artifacts if present
retire_legacy_a2abridge() {
  if [[ "$OS" == "linux" ]] && [[ -f "${HOME}/.config/systemd/user/a2abridge-directory.service" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      log "[dry-run] would stop and remove legacy a2abridge-directory.service"
    else
      systemctl --user disable --now a2abridge-directory.service >/dev/null 2>&1 || true
      rm -f "${HOME}/.config/systemd/user/a2abridge-directory.service"
      systemctl --user daemon-reload >/dev/null 2>&1 || true
      log "Retired legacy systemd service a2abridge-directory.service"
    fi
  fi
  for legacy_file in "${BIN_DIR}/a2abridge-mcp" "${BIN_DIR}/a2abridge" "${HOME}/.a2abridge/hooks/on-inbound.sh"; do
    if [[ -e "$legacy_file" ]]; then
      if [[ "$DRY_RUN" -eq 1 ]]; then
        log "[dry-run] would remove legacy file ${legacy_file}"
      else
        rm -f "$legacy_file"
        log "Removed legacy ${legacy_file}"
      fi
    fi
  done
}

retire_legacy_a2abridge

# 3. Install unified `labflow-a2a` executable
SRV_SRC="${SCRIPT_DIR}/labflow_a2a.py"
SRV_DST="${BIN_DIR}/labflow-a2a"
if [[ "$DRY_RUN" -eq 1 ]]; then
  log "[dry-run] would install ${SRV_SRC} -> ${SRV_DST}"
else
  mkdir -p "$BIN_DIR"
  install -m 0755 "$SRV_SRC" "$SRV_DST"
  log "Installed unified service -> ${SRV_DST}"
fi

# 4. Configure & start user-level `labflow-a2a` daemon (:7778 antigravity, :7779 codex)
if [[ "$SKIP_SERVICE" -eq 0 ]]; then
  if [[ "$OS" == "linux" ]]; then
    UNIT_DIR="${HOME}/.config/systemd/user"
    UNIT_FILE="${UNIT_DIR}/labflow-a2a.service"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      log "[dry-run] would write user systemd unit ${UNIT_FILE} and ensure active"
    else
      mkdir -p "$UNIT_DIR"
      UNIT_TMP="$(mktemp)"
      cat > "$UNIT_TMP" <<EOF
[Unit]
Description=Labflow Session-Addressable A2A 1.0 Workbench Service (:7778 antigravity, :7779 codex)
After=default.target

[Service]
ExecStart=/usr/bin/python3 ${SRV_DST} daemon
Environment="PATH=${BIN_DIR}:/usr/local/bin:/usr/bin:/bin"
Environment="DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/%U/bus"
PassEnvironment=DISPLAY WAYLAND_DISPLAY XAUTHORITY
StandardOutput=journal
StandardError=journal
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
      if [[ -f "$UNIT_FILE" ]] && cmp -s "$UNIT_TMP" "$UNIT_FILE" && systemctl --user is-active --quiet labflow-a2a.service; then
        rm -f "$UNIT_TMP"
        systemctl --user restart labflow-a2a.service
        log "Restarted systemd --user service labflow-a2a.service"
      else
        mv "$UNIT_TMP" "$UNIT_FILE"
        systemctl --user daemon-reload
        systemctl --user enable --now labflow-a2a.service
        systemctl --user restart labflow-a2a.service
        log "Started systemd --user service labflow-a2a.service (:7778 & :7779)"
      fi
    fi
  elif [[ "$OS" == "darwin" ]]; then
    PLIST_DIR="${HOME}/Library/LaunchAgents"
    PLIST_FILE="${PLIST_DIR}/dev.labflow.a2a.plist"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      log "[dry-run] would write macOS LaunchAgent ${PLIST_FILE}"
    else
      mkdir -p "$PLIST_DIR"
      cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>dev.labflow.a2a</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>python3</string>
    <string>${SRV_DST}</string>
    <string>daemon</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict>
</plist>
EOF
      launchctl unload "$PLIST_FILE" >/dev/null 2>&1 || true
      launchctl load "$PLIST_FILE"
      log "Loaded macOS LaunchAgent dev.labflow.a2a"
    fi
  fi
fi

# 5. Surgically register `a2a` MCP server in Antigravity & Codex host configs
python3 - "$SRV_DST" "$DRY_RUN" "$WITH_CLAUDE" <<'EOF'
import datetime, json, pathlib, re, shutil, sys, tomllib

srv_bin, dry_run_s, with_claude_s = sys.argv[1:4]
dry_run = dry_run_s == "1"
with_claude = with_claude_s == "1"
home = pathlib.Path.home()
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def backup_file(path: pathlib.Path) -> pathlib.Path:
    bak = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, bak)
    return bak

def patch_json_mcp(path: pathlib.Path, self_agent: str, include_disabled: bool) -> None:
    if not path.exists():
        print(f"[labflow/a2a] SKIP: {path} not present on this host")
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    servers = data.setdefault("mcpServers", {})
    desired = {
        "command": srv_bin,
        "args": ["mcp", "--self", self_agent],
    }
    if include_disabled:
        desired["disabled"] = False
    if servers.get("a2a") == desired:
        print(f"[labflow/a2a] OK: {path} already has matching 'a2a' MCP entry")
        return
    if dry_run:
        print(f"[labflow/a2a] [dry-run] would register 'a2a' ({self_agent}) in {path}")
        return
    bak = backup_file(path)
    servers.pop("a2abridge", None)
    servers["a2a"] = desired
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    json.loads(path.read_text(encoding="utf-8"))
    print(f"[labflow/a2a] Updated {path} (backup: {bak.name})")

def patch_codex_toml(path: pathlib.Path) -> None:
    if not path.exists():
        print(f"[labflow/a2a] SKIP: {path} not present on this host")
        return
    raw = path.read_text(encoding="utf-8")
    parsed = tomllib.loads(raw)
    existing = parsed.get("mcp_servers", {}).get("a2a")
    desired_args = ["mcp", "--self", "codex"]
    if existing and existing.get("command") == srv_bin and existing.get("args") == desired_args:
        print(f"[labflow/a2a] OK: {path} already has matching [mcp_servers.a2a]")
        return
    if dry_run:
        print(f"[labflow/a2a] [dry-run] would update [mcp_servers.a2a] in {path}")
        return
    bak = backup_file(path)
    new_block = (
        "[mcp_servers.a2a]\n"
        f'command = "{srv_bin}"\n'
        'args = ["mcp", "--self", "codex"]\n'
    )
    if existing is not None:
        # Replace only the `[mcp_servers.a2a]` section at EOF or before next `[section]`
        updated, count = re.subn(
            r"(?ms)^\[mcp_servers\.a2a\]\n(?:(?!\[).*\n?)*",
            new_block,
            raw,
            count=1,
        )
        if count == 0:
            raise RuntimeError(f"Could not safely replace [mcp_servers.a2a] in {path}")
    else:
        updated = raw.rstrip("\n") + "\n\n" + new_block
    tomllib.loads(updated)
    path.write_text(updated, encoding="utf-8")
    print(f"[labflow/a2a] Updated [mcp_servers.a2a] in {path} (backup: {bak.name})")

patch_json_mcp(home / ".gemini/antigravity/mcp_config.json", "antigravity", include_disabled=True)
patch_json_mcp(home / ".gemini/config/mcp_config.json", "antigravity", include_disabled=True)
patch_codex_toml(home / ".codex/config.toml")

if with_claude:
    patch_json_mcp(home / ".claude.json", "codex", include_disabled=False)
EOF

# 6. Register named contacts (`antigravity`, `codex`) in official `a2a` CLI contact book
if [[ "$DRY_RUN" -eq 0 && "$SKIP_SERVICE" -eq 0 && -x "${BIN_DIR}/a2a" ]]; then
  sleep 0.5
  "${BIN_DIR}/a2a" contact add --replace antigravity "http://127.0.0.1:7778" >/dev/null 2>&1 || true
  "${BIN_DIR}/a2a" contact add --replace codex "http://127.0.0.1:7779" >/dev/null 2>&1 || true
  log "Registered a2a CLI contacts: antigravity (:7778), codex (:7779)"
fi

log "Done. Run ./a2a/doctor.sh --e2e to verify."
