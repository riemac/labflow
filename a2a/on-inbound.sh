#!/bin/sh
# Labflow A2A 1.0 inbound hook (~/.a2abridge/hooks/on-inbound.sh).
# Must remain strict POSIX sh because a2abridge invokes `/bin/sh <script>` directly.
#
# Fired asynchronously by a2abridge whenever a peer sends a new A2A task.
# - For live Codex Desktop sessions (ancestor is Codex app-server, NOT headless
#   `codex exec`): resolves the active Codex Desktop thread UUID for the bridge's
#   working directory and triggers native `codex queue --thread <UUID>` so the
#   open Codex Desktop GUI wakes up, processes `a2a_inbox`, and replies via
#   `a2a_complete_task` automatically without manual window switching.
# - For Antigravity sessions: sends a non-intrusive desktop notification (if
#   `notify-send` is available), since Antigravity runs one shared MCP bridge
#   without a per-tab external queue API.

set -eu

# Opt-out escape hatch for debugging or manual-only workflows.
if [ "${LABFLOW_A2A_AUTO_WAKE:-1}" = "0" ]; then
  exit 0
fi

HOOK_DIR="${HOME}/.a2abridge/hooks"
LOG_FILE="${HOOK_DIR}/on-inbound.log"
SEEN_FILE="${HOOK_DIR}/nudged_tasks.log"
mkdir -p "$HOOK_DIR"

log() {
  printf '%s %s\n' "$(date -Iseconds 2>/dev/null || date)" "$*" >> "$LOG_FILE" 2>/dev/null || true
}

TASK_ID="${A2A_EVENT_TASK:-}"
FROM_PEER="${A2A_EVENT_FROM:-peer}"
CWD="$(pwd -P 2>/dev/null || pwd)"

# Inspect parent (a2abridge) and ancestor chain to identify peer and host runtime.
BRIDGE_ARGS="$(ps -o args= -p "$PPID" 2>/dev/null || true)"
PEER_NAME="${LABFLOW_A2A_PEER_NAME:-}"
if [ -z "$PEER_NAME" ]; then
  PEER_NAME="$(printf '%s\n' "$BRIDGE_ARGS" | sed -n 's/.*-name[= ]\([^ ]*\).*/\1/p' | head -n 1)"
fi

IS_CODEX_DESKTOP=0
IS_CODEX_EXEC=0
IS_ANTIGRAVITY=0
CUR_PID="$PPID"
for _ in 1 2 3 4 5; do
  NEXT_PID="$(ps -o ppid= -p "$CUR_PID" 2>/dev/null | tr -d ' ' || true)"
  if [ -z "$NEXT_PID" ] || [ "$NEXT_PID" -le 1 ] 2>/dev/null; then
    break
  fi
  CMD="$(ps -o args= -p "$NEXT_PID" 2>/dev/null || true)"
  case "$CMD" in
    *"codex exec"*|*"codex e "*)
      IS_CODEX_EXEC=1
      ;;
    *"/chatgpt/resources/codex"*|*"codex app-server"*)
      IS_CODEX_DESKTOP=1
      ;;
    *"antigravity"*)
      IS_ANTIGRAVITY=1
      ;;
  esac
  CUR_PID="$NEXT_PID"
done

# Deduplicate per taskId so the same task is never queued twice.
if [ -n "$TASK_ID" ]; then
  touch "$SEEN_FILE"
  if grep -Fqx "$TASK_ID" "$SEEN_FILE" 2>/dev/null; then
    log "SKIP duplicate task=$TASK_ID peer=$PEER_NAME"
    exit 0
  fi
  printf '%s\n' "$TASK_ID" >> "$SEEN_FILE"
  LINE_COUNT="$(wc -l < "$SEEN_FILE" 2>/dev/null | tr -d ' ' || echo 0)"
  if [ "$LINE_COUNT" -gt 500 ] 2>/dev/null; then
    tail -n 250 "$SEEN_FILE" > "${SEEN_FILE}.tmp" && mv "${SEEN_FILE}.tmp" "$SEEN_FILE"
  fi
fi

# Path 1: Auto-wake live Codex Desktop session via native `codex queue`.
if [ "$PEER_NAME" = "codex" ] && [ "$IS_CODEX_DESKTOP" -eq 1 ] && [ "$IS_CODEX_EXEC" -eq 0 ]; then
  THREAD_ID="$(python3 - "$CWD" <<'PY' 2>/dev/null || true
import json, os, pathlib, sys

target_cwd = os.path.realpath(sys.argv[1])
sessions_root = pathlib.Path.home() / ".codex" / "sessions"
if not sessions_root.exists():
    sys.exit(0)

candidates = []
for p in sessions_root.rglob("*.jsonl"):
    try:
        candidates.append((p.stat().st_mtime, p))
    except OSError:
        continue
candidates.sort(key=lambda x: x[0], reverse=True)

for _, path in candidates[:80]:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            first = f.readline()
        meta = json.loads(first).get("payload", {})
        if meta.get("originator") != "Codex Desktop" and meta.get("source") != "vscode":
            continue
        cwd = meta.get("cwd") or ""
        if cwd and os.path.realpath(cwd) == target_cwd and meta.get("id"):
            print(meta["id"])
            sys.exit(0)
    except Exception:
        continue
PY
)"

  if [ -z "$THREAD_ID" ]; then
    log "WARN no Codex Desktop thread matched cwd=$CWD task=$TASK_ID"
    exit 0
  fi

  CODEX_BIN=""
  if [ -x "/usr/lib/chatgpt/resources/codex" ]; then
    CODEX_BIN="/usr/lib/chatgpt/resources/codex"
  elif command -v codex >/dev/null 2>&1; then
    CODEX_BIN="$(command -v codex)"
  else
    for cand in "${HOME}"/.nvm/versions/node/*/bin/codex; do
      if [ -x "$cand" ]; then
        CODEX_BIN="$cand"
      fi
    done
  fi

  if [ -z "$CODEX_BIN" ]; then
    log "WARN codex binary not found; cannot queue task=$TASK_ID thread=$THREAD_ID"
    exit 0
  fi

  MSG="[A2A 1.0 自动通知 | from=${FROM_PEER} | task=${TASK_ID}] 收到新的 A2A 消息，请立即调用 a2a_inbox 读取详情，完成处理后调用 a2a_complete_task 回复对方。"
  if OUT="$("$CODEX_BIN" queue --thread "$THREAD_ID" --message "$MSG" 2>&1)"; then
    log "QUEUED codex thread=$THREAD_ID task=$TASK_ID from=$FROM_PEER cwd=$CWD out=$(printf '%s' "$OUT" | tr '\n' ' ')"
  else
    log "ERROR codex queue failed thread=$THREAD_ID task=$TASK_ID out=$(printf '%s' "$OUT" | tr '\n' ' ')"
  fi
  exit 0
fi

# Path 2: Non-intrusive desktop notification for Antigravity inbound messages.
case "$PEER_NAME" in
  antigravity*) IS_ANTIGRAVITY=1 ;;
esac
if [ "$IS_ANTIGRAVITY" -eq 1 ]; then
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "Labflow A2A: 新消息来自 ${FROM_PEER}" "Task ${TASK_ID} 已到达 Antigravity 收件箱，请让 Antigravity 检查 a2a_inbox。" >/dev/null 2>&1 || true
  fi
  log "NOTIFIED antigravity task=$TASK_ID from=$FROM_PEER"
  exit 0
fi

log "IGNORED peer=$PEER_NAME desktop=$IS_CODEX_DESKTOP exec=$IS_CODEX_EXEC task=$TASK_ID cwd=$CWD"
