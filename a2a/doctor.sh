#!/usr/bin/env bash
# Healthcheck & E2E verification for the Labflow Unified A2A 1.0 Service (v2.1.0).

set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
AGY_URL="${LABFLOW_A2A_AGY_URL:-http://127.0.0.1:7778}"
CODEX_URL="${LABFLOW_A2A_CODEX_URL:-http://127.0.0.1:7779}"
RUN_E2E=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --e2e) RUN_E2E=1 ;;
    -h|--help) echo "Usage: $0 [--e2e]"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
  shift
done

FAILURES=0
pass() { printf '  [PASS] %-26s %s\n' "$1" "$2"; }
warn() { printf '  [WARN] %-26s %s\n' "$1" "$2"; }
fail() { printf '  [FAIL] %-26s %s\n' "$1" "$2"; FAILURES=$((FAILURES + 1)); }

echo "Labflow A2A 1.0 Doctor (v2.1.1)"
echo "-------------------------------"

# 1. Binaries
if [[ -x "${BIN_DIR}/a2a" ]]; then
  pass "a2a CLI" "$("${BIN_DIR}/a2a" version 2>/dev/null | head -n 1)"
else
  fail "a2a CLI" "missing at ${BIN_DIR}/a2a"
fi

if [[ -x "${BIN_DIR}/labflow-a2a" ]]; then
  pass "labflow-a2a" "$("${BIN_DIR}/labflow-a2a" version 2>/dev/null | head -n 1)"
else
  fail "labflow-a2a" "missing at ${BIN_DIR}/labflow-a2a"
fi

# Ensure legacy a2abridge daemon is gone
if systemctl --user is-active --quiet a2abridge-directory.service 2>/dev/null; then
  fail "legacy a2abridge" "a2abridge-directory.service is still running (re-run ./a2a/install.sh)"
else
  pass "legacy cleanup" "no legacy a2abridge daemon active"
fi

# 2. Always-on A2A 1.0 Agent endpoints
for pair in "antigravity:${AGY_URL}" "codex:${CODEX_URL}"; do
  name="${pair%%:*}"
  url="${pair#*:}"
  if curl -fsS --max-time 3 "${url}/healthz" >/dev/null 2>&1; then
    pass "A2A Agent: ${name}" "${url} online"
  else
    fail "A2A Agent: ${name}" "${url} unreachable (check systemctl --user status labflow-a2a)"
  fi
done

# 3. Session Indexers + Host MCP Registrations
python3 - "${BIN_DIR}/labflow-a2a" "${AGY_URL}" <<'EOF' || FAILURES=$((FAILURES + 1))
import json, pathlib, sys, tomllib, urllib.request

srv_bin, agy_url = sys.argv[1:3]
home = pathlib.Path.home()
errors = 0

def check_json(label: str, path: pathlib.Path) -> None:
    global errors
    if not path.exists():
        print(f"  [WARN] {label:<26} not found ({path})")
        return
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        entry = d.get("mcpServers", {}).get("a2a")
        if entry and entry.get("command") == srv_bin and entry.get("args") == ["mcp", "--self", "antigravity"]:
            print(f"  [PASS] {label:<26} registered in {path}")
        else:
            print(f"  [FAIL] {label:<26} missing/stale 'a2a' entry in {path}")
            errors += 1
    except Exception as e:
        print(f"  [FAIL] {label:<26} invalid JSON: {e}")
        errors += 1

check_json("MCP: Antigravity App", home / ".gemini/antigravity/mcp_config.json")
check_json("MCP: Antigravity CLI", home / ".gemini/config/mcp_config.json")

codex_cfg = home / ".codex/config.toml"
if codex_cfg.exists():
    try:
        parsed = tomllib.loads(codex_cfg.read_text(encoding="utf-8"))
        entry = parsed.get("mcp_servers", {}).get("a2a")
        if entry and entry.get("command") == srv_bin and entry.get("args") == ["mcp", "--self", "codex"]:
            print(f"  [PASS] {'MCP: Codex':<26} registered in {codex_cfg}")
        else:
            print(f"  [FAIL] {'MCP: Codex':<26} missing/stale [mcp_servers.a2a] in {codex_cfg}")
            errors += 1
    except Exception as e:
        print(f"  [FAIL] {'MCP: Codex':<26} invalid TOML: {e}")
        errors += 1

# Verify read-only session index resolution on both sides
for ag in ("codex", "antigravity"):
    with urllib.request.urlopen(f"{agy_url}/internal/sessions?agent={ag}&limit=5", timeout=5) as r:
        sessions = json.loads(r.read().decode()).get("sessions", [])
    print(f"  [PASS] {'Sessions: ' + ag:<26} indexed {len(sessions)} recent session(s)")

sys.exit(1 if errors else 0)
EOF

# 4. Live E2E Protocol + Session-IRQ Round-Trip
if [[ "$RUN_E2E" -eq 1 && "$FAILURES" -eq 0 ]]; then
  python3 - "${BIN_DIR}/labflow-a2a" "${BIN_DIR}/a2a" "${AGY_URL}" "${CODEX_URL}" <<'EOF' || FAILURES=$((FAILURES + 1))
import json, subprocess, sys, threading, time, uuid

srv_bin, a2a_bin, agy_url, codex_url = sys.argv[1:5]

# 4a. Official `a2a card get` against both A2A 1.0 agents
for label, url in (("antigravity", agy_url), ("codex", codex_url)):
    c = subprocess.run([a2a_bin, "card", "get", url], capture_output=True, text=True, timeout=8)
    assert c.returncode == 0 and label in c.stdout, f"a2a card get failed for {label}: {c.stderr}"
print(f"  [PASS] {'E2E: a2a card get':<26} official a2a CLI verified both Agent Cards")

# 4b. Test race-free Linux inotify `wait-irq` + official `a2a send` blocking round-trip on synthetic session UUID!
synth_session = str(uuid.uuid4())
irq_proc = subprocess.Popen(
    [srv_bin, "wait-irq", "--agent", "antigravity", "--session", synth_session, "--timeout", "15"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)
time.sleep(0.3)

# Spawn MCP stdio client (`--self antigravity`) to read inbox & reply once IRQ wakes!
mcp = subprocess.Popen(
    [srv_bin, "mcp", "--self", "antigravity"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
)

def mcp_call(req_id: int, method: str, params: dict):
    mcp.stdin.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}) + "\n")
    mcp.stdin.flush()
    return json.loads(mcp.stdout.readline())

try:
    mcp_call(1, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "doc", "version": "1"}})
    tools = [t["name"] for t in mcp_call(2, "tools/list", {})["result"]["tools"]]
    assert "a2a_list_sessions" in tools and "a2a_send" in tools, f"Unexpected tools: {tools}"

    # Fire official `a2a send` (blocking!) from a background thread targeting `synth_session` via `--context-id`!
    send_holder = {}
    def run_official_send():
        send_holder["res"] = subprocess.run(
            [a2a_bin, "send", "-a", agy_url, "--context-id", synth_session, "e2e-irq-ping"],
            capture_output=True, text=True, timeout=15
        )
    t = threading.Thread(target=run_official_send)
    t.start()

    # `wait-irq` must wake immediately via Linux inotify!
    irq_out, irq_err = irq_proc.communicate(timeout=5)
    assert irq_proc.returncode == 0, f"wait-irq failed: {irq_err}"
    irq_data = json.loads(irq_out)
    assert irq_data["event"] == "inbound_task" and len(irq_data["inbox"]) == 1, irq_data
    tid = irq_data["inbox"][0]["task_id"]

    # Complete task via MCP `a2a_reply` -> must immediately unblock official `a2a send`!
    rep = mcp_call(3, "tools/call", {"name": "a2a_reply", "arguments": {"task_id": tid, "text": "e2e-irq-pong"}})
    assert not rep["result"]["isError"], rep

    t.join(timeout=5)
    sres = send_holder["res"]
    assert sres.returncode == 0 and "e2e-irq-pong" in sres.stdout, f"official a2a send failed: {sres.stdout} {sres.stderr}"
    print(f"  [PASS] {'E2E: IRQ + a2a send':<26} inotify wakeup + official a2a send/reply round-trip OK")
finally:
    mcp.terminate()
    if irq_proc.poll() is None:
        irq_proc.terminate()
EOF
fi

if [[ "$FAILURES" -gt 0 ]]; then
  echo "Doctor finished with ${FAILURES} failure(s)." >&2
  exit 1
fi
echo "All checks passed."
