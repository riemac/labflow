#!/usr/bin/env bash
# Healthcheck for the Labflow A2A 1.0 interoperability layer.
# Verifies binaries, local directory liveness, host MCP registrations,
# and (with --e2e) a live dual-peer MCP + official `a2a card get` round-trip.

set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
DIRECTORY_URL="${A2A_DIRECTORY_URL:-http://127.0.0.1:7777}"
RUN_E2E=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --e2e) RUN_E2E=1 ;;
    -h|--help)
      echo "Usage: $0 [--e2e]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
  shift
done

FAILURES=0
pass() { printf '  [PASS] %-24s %s\n' "$1" "$2"; }
warn() { printf '  [WARN] %-24s %s\n' "$1" "$2"; }
fail() { printf '  [FAIL] %-24s %s\n' "$1" "$2"; FAILURES=$((FAILURES + 1)); }

echo "Labflow A2A Doctor"
echo "------------------"

# 1. Binaries
if [[ -x "${BIN_DIR}/a2a" ]]; then
  pass "a2a CLI" "$("${BIN_DIR}/a2a" --version 2>/dev/null | head -n 1)"
else
  fail "a2a CLI" "missing at ${BIN_DIR}/a2a"
fi

if [[ -x "${BIN_DIR}/a2abridge" ]]; then
  pass "a2abridge" "$("${BIN_DIR}/a2abridge" version 2>/dev/null | head -n 1)"
else
  fail "a2abridge" "missing at ${BIN_DIR}/a2abridge"
fi

EXPECTED_MCP_CMD="${BIN_DIR}/a2abridge"
if [[ "$(uname -s)" == "Linux" ]]; then
  EXPECTED_MCP_CMD="${BIN_DIR}/a2abridge-mcp"
  if [[ -x "${EXPECTED_MCP_CMD}" ]]; then
    pass "a2abridge-mcp wrapper" "${EXPECTED_MCP_CMD}"
  else
    fail "a2abridge-mcp wrapper" "missing at ${EXPECTED_MCP_CMD} (run ./a2a/install.sh)"
  fi
fi

HOOK_DST="${HOME}/.a2abridge/hooks/on-inbound.sh"
if [[ -x "${HOOK_DST}" ]] && sh -n "${HOOK_DST}" 2>/dev/null; then
  pass "on-inbound hook" "${HOOK_DST} (POSIX sh OK)"
else
  warn "on-inbound hook" "missing or invalid at ${HOOK_DST} (run ./a2a/install.sh)"
fi

# 2. Local discovery directory
if AGENTS_JSON="$(curl -fsS --max-time 3 "${DIRECTORY_URL}/agents" 2>/dev/null)"; then
  PEER_COUNT="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(len(d) if isinstance(d,list) else "ok")' "$AGENTS_JSON" 2>/dev/null || echo "?")"
  pass "directory" "${DIRECTORY_URL} reachable (${PEER_COUNT} peer(s) online)"
else
  fail "directory" "${DIRECTORY_URL} unreachable (check systemctl --user status a2abridge-directory)"
fi

# 3. Host MCP registrations
python3 - "${EXPECTED_MCP_CMD}" <<'EOF' || FAILURES=$((FAILURES + 1))
import json, pathlib, sys, tomllib

bridge_bin = sys.argv[1]
home = pathlib.Path.home()
errors = 0

def check_json(label, path):
    global errors
    if not path.exists():
        print(f"  [WARN] {label:<24} not found ({path})")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = data.get("mcpServers", {}).get("a2a")
        if entry and entry.get("command") == bridge_bin and not entry.get("disabled", False):
            print(f"  [PASS] {label:<24} registered in {path}")
        else:
            print(f"  [FAIL] {label:<24} missing or disabled 'a2a' entry in {path}")
            errors += 1
    except Exception as e:
        print(f"  [FAIL] {label:<24} invalid JSON in {path}: {e}")
        errors += 1

check_json("MCP: Antigravity App", home / ".gemini/antigravity/mcp_config.json")
check_json("MCP: Antigravity CLI", home / ".gemini/config/mcp_config.json")

codex_cfg = home / ".codex/config.toml"
if codex_cfg.exists():
    try:
        parsed = tomllib.loads(codex_cfg.read_text(encoding="utf-8"))
        entry = parsed.get("mcp_servers", {}).get("a2a")
        if entry and entry.get("command") == bridge_bin:
            print(f"  [PASS] {'MCP: Codex':<24} registered in {codex_cfg}")
        else:
            print(f"  [FAIL] {'MCP: Codex':<24} missing [mcp_servers.a2a] in {codex_cfg}")
            errors += 1
    except Exception as e:
        print(f"  [FAIL] {'MCP: Codex':<24} invalid TOML in {codex_cfg}: {e}")
        errors += 1
else:
    print(f"  [WARN] {'MCP: Codex':<24} not found ({codex_cfg})")

sys.exit(1 if errors else 0)
EOF

# 4. Optional live E2E A2A 1.0 round-trip + multi-threaded parent survival check
if [[ "$RUN_E2E" -eq 1 && "$FAILURES" -eq 0 ]]; then
  python3 - "${EXPECTED_MCP_CMD}" "${BIN_DIR}/a2a" "${DIRECTORY_URL}" <<'EOF' || FAILURES=$((FAILURES + 1))
import json, subprocess, sys, tempfile, threading, time

bridge_cmd, a2a_bin, directory_url = sys.argv[1:4]

class MCPClient:
    def __init__(self, name, state_dir):
        holder = {}
        def spawner():
            holder["p"] = subprocess.Popen(
                [bridge_cmd, "bridge", "-name", name, "-directory", directory_url, "-state-dir", state_dir],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            time.sleep(0.35)  # Allow child PR_SET_PDEATHSIG setup before spawning thread exits
        t = threading.Thread(target=spawner)
        t.start()
        t.join()
        self.proc = holder["p"]
        self.req_id = 0

    def rpc(self, method, params=None):
        self.req_id += 1
        msg = {"jsonrpc": "2.0", "id": self.req_id, "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(self.proc.stderr.read())
            resp = json.loads(line)
            if resp.get("id") == self.req_id:
                return resp

    def init(self):
        self.rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "labflow-a2a-doctor", "version": "1.0"}
        })
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.proc.stdin.flush()

    def call(self, name, args=None):
        r = self.rpc("tools/call", {"name": name, "arguments": args or {}})
        txt = r["result"]["content"][0]["text"]
        try:
            return json.loads(txt)
        except Exception:
            return txt

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=3)
        except Exception:
            self.proc.kill()

with tempfile.TemporaryDirectory(prefix="labflow-a2a-e2e-") as td:
    a, b = MCPClient("doctor-peer-a", f"{td}/a"), MCPClient("doctor-peer-b", f"{td}/b")
    try:
        a.init(); b.init(); time.sleep(0.4)
        url_b = b.call("a2a_whoami")["supportedInterfaces"][0]["url"]
        card = subprocess.run([a2a_bin, "card", "get", url_b], capture_output=True, text=True, timeout=10)
        assert card.returncode == 0, card.stderr
        sent = a.call("a2a_send_message", {"peer_url": url_b, "text": "doctor-ping"})
        tid = sent["id"]
        inbox = b.call("a2a_inbox")
        assert any((t.get("taskId") or t.get("id") or t.get("task_id")) == tid for t in inbox), f"task {tid} missing in inbox: {inbox}"
        b.call("a2a_complete_task", {"task_id": tid, "text": "doctor-pong"})
        final = a.call("a2a_get_task", {"peer_url": url_b, "task_id": tid})
        assert final["status"]["state"] == "TASK_STATE_COMPLETED", final
        print(f"  [PASS] {'E2E A2A 1.0':<24} card get + send -> inbox -> complete -> get_task verified")
    finally:
        a.close(); b.close()
EOF
fi

if [[ "$FAILURES" -gt 0 ]]; then
  echo "Doctor finished with ${FAILURES} failure(s)." >&2
  exit 1
fi
echo "All checks passed."
