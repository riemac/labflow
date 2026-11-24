#!/usr/bin/env python3
"""Labflow Unified Session-Addressable A2A 1.0 Service, MCP Server, and IRQ Listener.

Architectural role (pure transport & addressing primitives, zero workflow policy):
  - Maps A2A 1.0 `Agent` 1:1 to each desktop workbench (`antigravity` on 127.0.0.1:7778,
    `codex` on 127.0.0.1:7779) so endpoints stay permanently online across GUI restarts.
  - Maps A2A 1.0 `contextId` 1:1 to a concrete GUI conversation/session (`conversation_id`
    in Antigravity App; `thread_id` in Codex Desktop App), addressable by UUID, title
    substring, `latest`, or `new` (for Codex).
  - Never applies hidden fallback policies: messages targeting an Antigravity App session
    stay strictly in that session's isolated mailbox (never silently cloned into `agy` CLI).
  - Provides three subcommands in one zero-dependency Python 3.12 executable:
      1. `daemon`   : Always-on A2A 1.0 HTTP/JSON-RPC + REST server for both agents.
      2. `mcp`      : Thin stdio MCP server exposing 6 deterministic session/task primitives.
      3. `wait-irq` : Race-free Linux `inotify` zero-CPU interrupt blocker for Antigravity tabs.
"""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import glob
import http.server
import json
import os
import pathlib
import select
import signal
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

VERSION = "2.1.0"
ANTIGRAVITY_PORT = int(os.environ.get("LABFLOW_A2A_AGY_PORT", "7778"))
CODEX_PORT = int(os.environ.get("LABFLOW_A2A_CODEX_PORT", "7779"))
BIND_HOST = "127.0.0.1"

AGENTS_CONFIG: dict[str, dict[str, Any]] = {
    "antigravity": {
        "name": "antigravity",
        "port": ANTIGRAVITY_PORT,
        "url": f"http://{BIND_HOST}:{ANTIGRAVITY_PORT}",
        "description": "Labflow A2A 1.0 Workbench Agent for Google Antigravity App (session-addressable via contextId).",
    },
    "codex": {
        "name": "codex",
        "port": CODEX_PORT,
        "url": f"http://{BIND_HOST}:{CODEX_PORT}",
        "description": "Labflow A2A 1.0 Workbench Agent for OpenAI Codex Desktop App (hot/cold session revival via contextId).",
    },
}


def utc_now_iso() -> str:
    """Return current UTC timestamp in RFC3339 millisecond format."""
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def state_root() -> pathlib.Path:
    """Return host-local state directory (~/.local/state/labflow-a2a)."""
    custom = os.environ.get("LABFLOW_A2A_STATE_DIR")
    base = pathlib.Path(custom) if custom else (pathlib.Path.home() / ".local" / "state" / "labflow-a2a")
    base.mkdir(parents=True, exist_ok=True)
    return base


def atomic_write_json(path: pathlib.Path, payload: Any) -> None:
    """Write JSON atomically via same-directory temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def is_pid_alive(pid: int) -> bool:
    """Check whether a local process ID is currently alive."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def session_dir_for(agent: str, session_id: str) -> pathlib.Path:
    """Return isolated runtime directory for a specific (agent, session_id)."""
    safe_id = session_id.replace("/", "_")
    d = state_root() / "sessions" / agent / safe_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def check_irq_armed(agent: str, session_id: str) -> bool:
    """Return True if a live `wait-irq` listener is currently armed on (agent, session_id)."""
    armed_file = session_dir_for(agent, session_id) / "armed.json"
    if not armed_file.exists():
        return False
    try:
        info = json.loads(armed_file.read_text(encoding="utf-8"))
        pid = int(info.get("pid", 0))
        if is_pid_alive(pid):
            return True
        armed_file.unlink(missing_ok=True)
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Read-only Session Indexers (Codex Desktop & Antigravity App)
# ---------------------------------------------------------------------------


def find_codex_binary(prefer_desktop: bool = False) -> str:
    """Locate an installed Codex executable for queue / app-server operations."""
    desktop_bin = "/usr/lib/chatgpt/resources/codex"
    candidates: list[str] = []
    if prefer_desktop:
        candidates.append(desktop_bin)
    # Check standard PATH and NVM installations
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if directory:
            candidates.append(os.path.join(directory, "codex"))
    candidates.extend(sorted(glob.glob(str(pathlib.Path.home() / ".nvm/versions/node/*/bin/codex")), reverse=True))
    if not prefer_desktop:
        candidates.append(desktop_bin)
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    raise RuntimeError("Codex binary not found on PATH, ~/.nvm, or /usr/lib/chatgpt/resources/codex")


def build_codex_env(codex_bin: str = "") -> dict[str, str]:
    """Build subprocess env with NVM node bin directories on PATH (required under systemd --user)."""
    env = dict(os.environ)
    extra_dirs: list[str] = []
    if codex_bin:
        extra_dirs.append(os.path.dirname(os.path.abspath(codex_bin)))
    extra_dirs.extend(sorted(glob.glob(str(pathlib.Path.home() / ".nvm/versions/node/*/bin")), reverse=True))
    extra_dirs.append(str(pathlib.Path.home() / ".local" / "bin"))
    cur_path = env.get("PATH", "")
    merged = [d for d in extra_dirs if d and os.path.isdir(d)]
    if cur_path:
        merged.append(cur_path)
    env["PATH"] = os.pathsep.join(merged)
    return env


def list_codex_sessions(query: str = "", cwd: str = "", limit: int = 20, include_exec: bool = False) -> list[dict[str, Any]]:
    """Read-only scan of ~/.codex/session_index.jsonl and recent rollout headers."""
    home = pathlib.Path.home()
    codex_home = pathlib.Path(os.environ.get("CODEX_HOME", str(home / ".codex")))
    index_map: dict[str, dict[str, Any]] = {}

    sidx = codex_home / "session_index.jsonl"
    if sidx.exists():
        try:
            for line in sidx.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    sid = item.get("id")
                    if sid:
                        index_map[sid] = {
                            "session_id": sid,
                            "title": item.get("thread_name") or "",
                            "updated_at": item.get("updated_at") or "",
                            "cwd": "",
                            "source": "vscode",
                            "originator": "Codex Desktop",
                        }
                except Exception:
                    continue
        except OSError:
            pass

    # Enrich with cwd/source/mtime from recent rollout files (bounded to newest 250 files).
    sessions_root = codex_home / "sessions"
    if sessions_root.exists():
        rollouts: list[tuple[float, pathlib.Path]] = []
        for p in sessions_root.rglob("*.jsonl"):
            try:
                rollouts.append((p.stat().st_mtime, p))
            except OSError:
                continue
        rollouts.sort(key=lambda x: x[0], reverse=True)

        for mtime, path in rollouts[:250]:
            try:
                with path.open("r", encoding="utf-8", errors="ignore") as f:
                    first = f.readline()
                meta = json.loads(first).get("payload", {})
                sid = meta.get("id") or meta.get("session_id")
                if not sid:
                    continue
                iso_mtime = dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                rec = index_map.get(sid, {
                    "session_id": sid,
                    "title": "",
                    "updated_at": iso_mtime,
                })
                if not rec.get("updated_at") or iso_mtime > rec["updated_at"]:
                    rec["updated_at"] = iso_mtime
                rec["cwd"] = meta.get("cwd") or rec.get("cwd") or ""
                rec["source"] = meta.get("source") or rec.get("source") or ""
                rec["originator"] = meta.get("originator") or rec.get("originator") or ""
                index_map[sid] = rec
            except Exception:
                continue

    target_cwd = os.path.realpath(cwd) if cwd else ""
    q = query.strip().lower()
    results: list[dict[str, Any]] = []

    for rec in index_map.values():
        # Exclude headless `codex exec` runs unless caller searched for an exact UUID.
        if not include_exec and rec.get("source") == "exec" and q != rec["session_id"].lower():
            continue
        if target_cwd:
            rcwd = rec.get("cwd") or ""
            if not rcwd or os.path.realpath(rcwd) != target_cwd:
                continue
        if q:
            hay = f"{rec['session_id']} {rec.get('title', '')} {rec.get('cwd', '')}".lower()
            if q not in hay:
                continue
        rec["agent"] = "codex"
        results.append(rec)

    results.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return results[: max(1, limit)]


def list_antigravity_sessions(query: str = "", cwd: str = "", limit: int = 20) -> list[dict[str, Any]]:
    """Read-only scan of ~/.gemini/antigravity/conversation_summaries.db for App conversations."""
    db_path = pathlib.Path.home() / ".gemini" / "antigravity" / "conversation_summaries.db"
    if not db_path.exists():
        return []

    target_cwd = os.path.realpath(cwd) if cwd else ""
    q = query.strip().lower()
    results: list[dict[str, Any]] = []

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=3.0)
    try:
        cur = con.cursor()
        rows = cur.execute(
            """
            SELECT conversation_id, title, preview, last_modified_time, workspace_uris, status, source
            FROM conversation_summaries
            WHERE killed = 0
            ORDER BY last_modified_time DESC
            LIMIT 200
            """
        ).fetchall()
    finally:
        con.close()

    for cid, title, preview, mod_time, ws_raw, status, source in rows:
        # Strictly target Antigravity App sessions (never CLI clones).
        if source == "CORTEX_TRAJECTORY_SOURCE_CLI" and q != (cid or "").lower():
            continue
        workspaces: list[str] = []
        if ws_raw:
            try:
                parsed_ws = json.loads(ws_raw)
                if isinstance(parsed_ws, list):
                    for u in parsed_ws:
                        if isinstance(u, str):
                            workspaces.append(urllib.parse.unquote(u.removeprefix("file://")))
            except Exception:
                pass
        primary_cwd = workspaces[0] if workspaces else ""
        if target_cwd:
            if not any(os.path.realpath(w) == target_cwd for w in workspaces if w):
                continue
        display_title = (title or preview or "").strip()
        if q:
            hay = f"{cid} {display_title} {primary_cwd}".lower()
            if q not in hay:
                continue
        results.append({
            "agent": "antigravity",
            "session_id": cid,
            "title": display_title,
            "cwd": primary_cwd,
            "status": status or "",
            "updated_at": mod_time or "",
            "irq_armed": check_irq_armed("antigravity", cid),
        })
        if len(results) >= max(1, limit):
            break

    return results


def start_codex_app_server() -> tuple[subprocess.Popen[str], Any, Any]:
    """Spawn `codex app-server --stdio` with Codex Desktop client identity and return (proc, send_rpc, wait_id)."""
    app_bin = find_codex_binary(prefer_desktop=True)
    proc = subprocess.Popen(
        [app_bin, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=build_codex_env(app_bin),
    )
    assert proc.stdin and proc.stdout

    def send_rpc(msg: dict[str, Any]) -> None:
        assert proc.stdin
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def wait_id(target_id: int, timeout_s: float = 15.0) -> dict[str, Any]:
        assert proc.stdout
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            rlist, _, _ = select.select([proc.stdout], [], [], max(0.1, deadline - time.time()))
            if not rlist:
                break
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("EOF from app-server")
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("id") == target_id:
                return obj
        raise TimeoutError(f"Timed out waiting for app-server rpc id={target_id}")

    send_rpc({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"clientInfo": {"name": "Codex Desktop", "version": "26.1120.41243"}},
    })
    init_resp = wait_id(1)
    if "error" in init_resp:
        proc.terminate()
        raise RuntimeError(str(init_resp["error"]))
    send_rpc({"jsonrpc": "2.0", "method": "initialized"})
    return proc, send_rpc, wait_id


def drive_app_server_turn_async(proc: subprocess.Popen[str], thread_id: str, prompt: str) -> None:
    """Drive `turn/start` to `turn/completed` in a daemon thread so cold/new turns never abort early."""
    def _worker() -> None:
        try:
            assert proc.stdin and proc.stdout
            proc.stdin.write(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "turn/start",
                    "params": {"threadId": thread_id, "input": [{"type": "text", "text": prompt}]},
                })
                + "\n"
            )
            proc.stdin.flush()
            deadline = time.time() + 600.0
            while time.time() < deadline:
                rlist, _, _ = select.select([proc.stdout], [], [], max(0.5, deadline - time.time()))
                if not rlist:
                    break
                line = proc.stdout.readline()
                if not line:
                    break
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("method") == "turn/completed":
                    break
        except Exception:
            pass
        finally:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

    threading.Thread(target=_worker, daemon=True).start()


def create_new_codex_session(cwd: str = "") -> tuple[str, subprocess.Popen[str]]:
    """Start a fresh workbench-visible Codex thread via `app-server --stdio` and return (thread_id, open_proc)."""
    work_dir = os.path.realpath(cwd) if cwd else str(pathlib.Path.home())
    os.makedirs(work_dir, exist_ok=True)
    proc, send_rpc, wait_id = start_codex_app_server()
    try:
        send_rpc({"jsonrpc": "2.0", "id": 2, "method": "thread/start", "params": {"cwd": work_dir}})
        resp = wait_id(2)
        if "error" in resp:
            raise RuntimeError(str(resp["error"]))
        tid = resp.get("result", {}).get("thread", {}).get("id")
        if not tid:
            raise RuntimeError(f"No thread.id returned: {resp}")
        return str(tid), proc
    except Exception:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        raise


# ---------------------------------------------------------------------------
# Task Store & Dispatch Coordinator (Inside Daemon)
# ---------------------------------------------------------------------------


class TaskCoordinator:
    """Thread-safe A2A 1.0 task store, session resolver, and wakeup dispatcher."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._tasks_dir = state_root() / "tasks"
        self._tasks_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, dict[str, Any]] = {}
        self._load_existing()

    def _load_existing(self) -> None:
        for p in self._tasks_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("id"):
                    self._tasks[data["id"]] = data
            except Exception:
                continue

    def _persist(self, task: dict[str, Any]) -> None:
        atomic_write_json(self._tasks_dir / f"{task['id']}.json", task)

    def pending_count(self, agent: str, session_id: str) -> int:
        with self._cond:
            return sum(
                1
                for t in self._tasks.values()
                if t.get("_targetAgent") == agent
                and t.get("contextId") == session_id
                and t.get("status", {}).get("state") in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING")
            )

    def resolve_session(self, agent: str, session_spec: str, cwd: str = "") -> tuple[str, dict[str, Any]]:
        """Deterministically map `session_spec` (UUID | title | latest | new) -> (session_id, session_meta)."""
        spec = (session_spec or "latest").strip()

        if agent == "codex":
            if spec.lower() == "new":
                new_id, new_proc = create_new_codex_session(cwd=cwd)
                return new_id, {
                    "session_id": new_id,
                    "title": "(new session)",
                    "cwd": cwd or str(pathlib.Path.home()),
                    "_new_proc": new_proc,
                }

            sessions = list_codex_sessions(limit=200, include_exec=True)
            # 1. Exact UUID match
            for s in sessions:
                if s["session_id"].lower() == spec.lower():
                    return s["session_id"], s
            # If spec looks like a valid UUID (e.g. newly created thread before rollout flush), accept directly.
            try:
                uuid.UUID(spec)
                return spec, {"session_id": spec, "title": "", "cwd": cwd}
            except ValueError:
                pass

            workbench_sessions = [s for s in sessions if s.get("source") != "exec"]
            if cwd:
                real_cwd = os.path.realpath(cwd)
                scoped = [s for s in workbench_sessions if s.get("cwd") and os.path.realpath(s["cwd"]) == real_cwd]
            else:
                scoped = workbench_sessions

            if spec.lower() in ("latest", "auto", ""):
                if not scoped:
                    raise ValueError(f"No existing Codex workbench session found (cwd={cwd!r}). Pass session='new' to create one.")
                return scoped[0]["session_id"], scoped[0]

            # 2. Exact title match (case-insensitive), then substring match
            exact_title = [s for s in scoped if (s.get("title") or "").strip().lower() == spec.lower()]
            if exact_title:
                return exact_title[0]["session_id"], exact_title[0]
            sub_match = [s for s in scoped if spec.lower() in f"{s.get('title', '')} {s.get('cwd', '')}".lower()]
            if sub_match:
                return sub_match[0]["session_id"], sub_match[0]

            sample = ", ".join(f"{s['session_id'][:8]}({s.get('title') or s.get('cwd')})" for s in workbench_sessions[:5])
            raise ValueError(f"Codex session {spec!r} not found. Recent sessions: [{sample}]")

        if agent == "antigravity":
            if spec.lower() == "new":
                raise ValueError(
                    "Antigravity App does not expose an API to open a new GUI tab externally; "
                    "open a tab in Antigravity App first or target an existing session ID/title."
                )
            sessions = list_antigravity_sessions(limit=200)
            for s in sessions:
                if s["session_id"].lower() == spec.lower():
                    return s["session_id"], s
            try:
                uuid.UUID(spec)
                return spec, {"session_id": spec, "title": "", "cwd": cwd}
            except ValueError:
                pass

            scoped = sessions
            if cwd:
                real_cwd = os.path.realpath(cwd)
                scoped = [s for s in sessions if s.get("cwd") and os.path.realpath(s["cwd"]) == real_cwd]

            if spec.lower() in ("latest", "auto", ""):
                # Prefer an IRQ-armed tab if available, otherwise most recently modified App tab.
                armed = [s for s in scoped if s.get("irq_armed")]
                chosen = armed[0] if armed else (scoped[0] if scoped else None)
                if not chosen:
                    raise ValueError("No Antigravity App session found.")
                return chosen["session_id"], chosen

            exact_title = [s for s in scoped if (s.get("title") or "").strip().lower() == spec.lower()]
            if exact_title:
                return exact_title[0]["session_id"], exact_title[0]
            sub_match = [s for s in scoped if spec.lower() in (s.get("title") or "").lower()]
            if sub_match:
                return sub_match[0]["session_id"], sub_match[0]

            sample = ", ".join(f"{s['session_id'][:8]}({s.get('title')})" for s in sessions[:5])
            raise ValueError(f"Antigravity session {spec!r} not found. Recent App sessions: [{sample}]")

        raise ValueError(f"Unknown local agent: {agent!r}")

    def _public_task(self, task: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in task.items() if not k.startswith("_")}

    def create_and_dispatch(
        self,
        target_agent: str,
        text: str,
        session_spec: str = "",
        cwd: str = "",
        sender: str = "peer",
        message_id: str = "",
        extra_meta: dict[str, Any] | None = None,
        blocking: bool = True,
        timeout_sec: float = 90.0,
    ) -> dict[str, Any]:
        """Resolve target session, persist WORKING task, trigger native wakeup, and optionally block."""
        session_id, session_meta = self.resolve_session(target_agent, session_spec or "latest", cwd=cwd)
        task_id = str(uuid.uuid4())
        msg_id = message_id or str(uuid.uuid4())
        now = utc_now_iso()

        msg_metadata: dict[str, Any] = {
            "from": sender,
            "targetAgent": target_agent,
            "targetSessionId": session_id,
            "targetSessionTitle": session_meta.get("title") or "",
        }
        if extra_meta:
            msg_metadata.update(extra_meta)

        user_msg = {
            "messageId": msg_id,
            "contextId": session_id,
            "taskId": task_id,
            "role": "ROLE_USER",
            "parts": [{"text": text}],
            "metadata": msg_metadata,
        }

        task: dict[str, Any] = {
            "id": task_id,
            "contextId": session_id,
            "history": [user_msg],
            "status": {
                "state": "TASK_STATE_WORKING",
                "timestamp": now,
            },
            "metadata": {
                "targetAgent": target_agent,
                "targetSessionId": session_id,
                "targetSessionTitle": session_meta.get("title") or "",
                "from": sender,
            },
            "_targetAgent": target_agent,
        }

        with self._cond:
            self._tasks[task_id] = task
            self._persist(task)

        # Trigger deterministic host-specific wakeup (outside lock).
        delivery = self._wake_target(target_agent, session_id, session_meta, task_id, sender, text)
        with self._cond:
            task["metadata"]["delivery"] = delivery
            self._persist(task)

            if blocking and timeout_sec > 0:
                deadline = time.time() + timeout_sec
                while task["status"]["state"] in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING"):
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        break
                    self._cond.wait(timeout=remaining)

            return self._public_task(task)

    def _wake_target(
        self,
        target_agent: str,
        session_id: str,
        session_meta: dict[str, Any],
        task_id: str,
        sender: str,
        text: str,
    ) -> str:
        """Trigger native `codex queue --resume` or Antigravity `inotify` IRQ signal."""
        sdir = session_dir_for(target_agent, session_id)
        # Write IRQ trigger file atomically -> wakes any `inotify` listener in <1ms.
        atomic_write_json(
            sdir / "irq.json",
            {"taskId": task_id, "contextId": session_id, "from": sender, "ts": utc_now_iso()},
        )

        if target_agent == "codex":
            prompt = (
                f"[A2A 1.0 入站任务 | from={sender} | task_id={task_id} | session={session_id}] "
                f"请立即调用 MCP 工具 `a2a_inbox`（传 session='{session_id}'）读取消息全文，"
                f"处理后必须调用 `a2a_reply(task_id='{task_id}', text=...)` 将结果回传给对方。"
            )
            new_proc: subprocess.Popen[str] | None = session_meta.pop("_new_proc", None)
            if new_proc is not None:
                drive_app_server_turn_async(new_proc, session_id, prompt)
                return "codex_new_session_started"

            # Existing Codex session: try `thread/resume` on `app-server` first.
            # - If the session is COLD (not currently open in Codex Desktop), `thread/resume` succeeds
            #   and `drive_app_server_turn_async` keeps the connection alive until `turn/completed`
            #   (avoiding `<turn_aborted>` from short-lived CLI exits).
            # - If the session is HOT in Codex Desktop (`already has an active writer`), close the
            #   probe and dispatch via native `codex queue --thread <id>` so the open GUI wakes live!
            probe_proc: subprocess.Popen[str] | None = None
            try:
                probe_proc, send_rpc, wait_id = start_codex_app_server()
                send_rpc({"jsonrpc": "2.0", "id": 2, "method": "thread/resume", "params": {"threadId": session_id}})
                resume_resp = wait_id(2, timeout_s=12.0)
                if "error" not in resume_resp:
                    drive_app_server_turn_async(probe_proc, session_id, prompt)
                    probe_proc = None  # ownership transferred to async turn driver
                    return "codex_cold_session_resumed"
                err_str = json.dumps(resume_resp["error"])
                probe_proc.terminate()
                probe_proc.wait(timeout=2)
                probe_proc = None
                if "active writer" not in err_str:
                    # Unexpected resume error; still attempt `codex queue` below as fallback
                    pass
            except Exception:
                if probe_proc is not None:
                    try:
                        probe_proc.terminate()
                    except Exception:
                        pass

            try:
                codex_cli = find_codex_binary(prefer_desktop=True)
                res = subprocess.run(
                    [codex_cli, "queue", "--thread", session_id, "--message", prompt],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    env=build_codex_env(codex_cli),
                )
                out = (res.stdout + " " + res.stderr).strip()
                if res.returncode == 0:
                    return "codex_hot_gui_queued"
                return f"codex_queue_error: {out[:160]}"
            except Exception as e:
                return f"codex_queue_exception: {e}"

        if target_agent == "antigravity":
            if check_irq_armed("antigravity", session_id):
                return "antigravity_irq_woken"
            title = session_meta.get("title") or session_id[:8]
            try:
                subprocess.run(
                    [
                        "notify-send",
                        f"A2A → Antigravity [{title}]",
                        f"来自 {sender} 的消息已进入会话 [{title}] 收件箱（task {task_id[:8]}）",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
            except Exception:
                pass
            return "queued_in_session_inbox_irq_unarmed"

        return "queued"

    def get_task(self, task_id: str) -> dict[str, Any]:
        with self._cond:
            t = self._tasks.get(task_id)
            if not t:
                raise KeyError(f"Task {task_id!r} not found")
            return self._public_task(t)

    def list_tasks(self, agent: str = "", context_id: str = "", limit: int = 50) -> list[dict[str, Any]]:
        with self._cond:
            items = list(self._tasks.values())
            if agent:
                items = [t for t in items if t.get("_targetAgent") == agent]
            if context_id:
                items = [t for t in items if t.get("contextId") == context_id]
            items.sort(key=lambda t: t.get("status", {}).get("timestamp") or "", reverse=True)
            return [self._public_task(t) for t in items[:limit]]

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        with self._cond:
            t = self._tasks.get(task_id)
            if not t:
                raise KeyError(f"Task {task_id!r} not found")
            if t["status"]["state"] in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING"):
                t["status"] = {"state": "TASK_STATE_CANCELED", "timestamp": utc_now_iso()}
                self._persist(t)
                self._cond.notify_all()
            return self._public_task(t)

    def get_inbox(self, agent: str, session_id: str) -> list[dict[str, Any]]:
        """Return pending WORKING/SUBMITTED tasks addressed to (agent, session_id)."""
        with self._cond:
            pending: list[dict[str, Any]] = []
            for t in self._tasks.values():
                if t.get("_targetAgent") != agent:
                    continue
                if session_id and t.get("contextId") != session_id:
                    continue
                if t.get("status", {}).get("state") not in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING"):
                    continue
                first_msg = (t.get("history") or [{}])[0]
                text = "".join(p.get("text", "") for p in first_msg.get("parts", []) if isinstance(p, dict))
                pending.append({
                    "task_id": t["id"],
                    "session_id": t["contextId"],
                    "from": t.get("metadata", {}).get("from", "peer"),
                    "text": text,
                    "timestamp": t.get("status", {}).get("timestamp", ""),
                })
            pending.sort(key=lambda x: x.get("timestamp") or "")
            return pending

    def complete_task(self, task_id: str, reply_text: str, responder: str = "") -> dict[str, Any]:
        """Attach reply Artifact, mark COMPLETED, and immediately wake any blocking caller."""
        with self._cond:
            t = self._tasks.get(task_id)
            if not t:
                raise KeyError(f"Task {task_id!r} not found")
            now = utc_now_iso()
            reply_msg = {
                "messageId": str(uuid.uuid4()),
                "contextId": t["contextId"],
                "taskId": task_id,
                "role": "ROLE_AGENT",
                "parts": [{"text": reply_text}],
            }
            if responder:
                reply_msg["metadata"] = {"responder": responder}
            t.setdefault("history", []).append(reply_msg)
            t["artifacts"] = [
                {
                    "artifactId": str(uuid.uuid4()),
                    "name": "reply",
                    "parts": [{"text": reply_text}],
                }
            ]
            t["status"] = {
                "state": "TASK_STATE_COMPLETED",
                "message": reply_msg,
                "timestamp": now,
            }
            self._persist(t)
            self._cond.notify_all()
            return self._public_task(t)


# ---------------------------------------------------------------------------
# Standard A2A 1.0 HTTP Server (JSON-RPC + HTTP/JSON + Internal MCP Helper API)
# ---------------------------------------------------------------------------


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], agent_name: str, coord: TaskCoordinator):
        self.agent_name = agent_name
        self.coord = coord
        super().__init__(server_address, A2ARequestHandler)


def build_agent_card(agent_name: str) -> dict[str, Any]:
    cfg = AGENTS_CONFIG[agent_name]
    url = cfg["url"]
    return {
        "name": cfg["name"],
        "description": cfg["description"],
        "version": VERSION,
        "supportedInterfaces": [
            {"url": url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"},
            {"url": url, "protocolBinding": "HTTP+JSON", "protocolVersion": "1.0"},
        ],
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "workbench-session-messaging",
                "name": "Workbench Session Messaging",
                "description": "Address a specific GUI conversation via contextId or metadata.session (UUID, title, latest, or new).",
                "tags": ["a2a", "workbench", agent_name],
            }
        ],
        "provider": {
            "organization": "labflow",
            "url": "https://a2a-protocol.org/latest/",
        },
    }


class A2ARequestHandler(http.server.BaseHTTPRequestHandler):
    server: ThreadedHTTPServer

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: Any) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("A2A-Version", "1.0")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        agent = self.server.agent_name
        coord = self.server.coord

        if path in ("/.well-known/agent-card.json", "/.well-known/agent.json", "/agent-card.json"):
            self._send_json(200, build_agent_card(agent))
            return

        if path == "/healthz":
            self._send_json(200, {"ok": True, "agent": agent, "version": VERSION})
            return

        if path in ("/tasks", "/v1/tasks"):
            ctx_id = (qs.get("contextId") or [""])[0]
            self._send_json(200, {"tasks": coord.list_tasks(agent=agent, context_id=ctx_id)})
            return

        if path.startswith("/tasks/") or path.startswith("/v1/tasks/"):
            tid = path.rstrip("/").split("/")[-1]
            try:
                self._send_json(200, coord.get_task(tid))
            except KeyError as e:
                self._send_json(404, {"error": {"code": 404, "message": str(e)}})
            return

        if path == "/internal/sessions":
            target = (qs.get("agent") or [agent])[0]
            q = (qs.get("query") or [""])[0]
            cwd = (qs.get("cwd") or [""])[0]
            limit = int((qs.get("limit") or ["20"])[0])
            sessions = (
                list_codex_sessions(query=q, cwd=cwd, limit=limit)
                if target == "codex"
                else list_antigravity_sessions(query=q, cwd=cwd, limit=limit)
            )
            for s in sessions:
                s["pending_inbox_count"] = coord.pending_count(target, s["session_id"])
            self._send_json(200, {"sessions": sessions})
            return

        if path == "/internal/inbox":
            target = (qs.get("agent") or [agent])[0]
            sid = (qs.get("session_id") or [""])[0]
            self._send_json(200, {"inbox": coord.get_inbox(target, sid)})
            return

        self._send_json(404, {"error": {"code": 404, "message": f"Unknown path {path}"}})

    def _handle_send_params(self, params: dict[str, Any]) -> dict[str, Any]:
        msg = params.get("message") or {}
        parts = msg.get("parts") or []
        text = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p)
        meta = dict(params.get("metadata") or {})
        msg_meta = msg.get("metadata") or {}
        if isinstance(msg_meta, dict):
            meta.update(msg_meta)

        # Standard A2A contextId maps directly to session_spec unless metadata.session overrides it.
        session_spec = str(meta.get("session") or msg.get("contextId") or "latest")
        cwd = str(meta.get("cwd") or "")
        sender = str(meta.get("from") or "a2a-client")

        cfg = params.get("configuration") or {}
        # A2A 1.0: blocking defaults to True unless configuration.returnImmediately / blocking=False is set.
        blocking = True
        if cfg.get("returnImmediately") is True or cfg.get("blocking") is False or meta.get("blocking") is False:
            blocking = False
        timeout_sec = float(meta.get("timeout_sec", 90.0))

        return self.server.coord.create_and_dispatch(
            target_agent=self.server.agent_name,
            text=text,
            session_spec=session_spec,
            cwd=cwd,
            sender=sender,
            message_id=str(msg.get("messageId") or ""),
            extra_meta=meta,
            blocking=blocking,
            timeout_sec=timeout_sec,
        )

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        coord = self.server.coord

        try:
            body = self._read_json()
        except Exception as e:
            self._send_json(400, {"error": {"code": -32700, "message": f"Invalid JSON: {e}"}})
            return

        # Internal reply endpoint used by `labflow-a2a mcp`
        if path == "/internal/reply":
            try:
                task = coord.complete_task(
                    task_id=str(body["task_id"]),
                    reply_text=str(body["text"]),
                    responder=str(body.get("responder") or self.server.agent_name),
                )
                self._send_json(200, {"task": task})
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        # HTTP+JSON REST bindings (`/message:send`, `/v1/message:send`, `/tasks/{id}:cancel`)
        if path in ("/message:send", "/v1/message:send"):
            try:
                task = self._handle_send_params(body)
                self._send_json(200, {"task": task})
            except Exception as e:
                self._send_json(400, {"error": {"code": 400, "message": str(e)}})
            return

        if path.endswith(":cancel"):
            tid = path.split("/")[-1].removesuffix(":cancel")
            try:
                self._send_json(200, coord.cancel_task(tid))
            except KeyError as e:
                self._send_json(404, {"error": {"code": 404, "message": str(e)}})
            return

        # JSON-RPC 2.0 binding (`POST /`)
        if "method" in body:
            req_id = body.get("id")
            method = str(body.get("method") or "")
            params = body.get("params") or {}
            try:
                if method in ("SendMessage", "message/send"):
                    task = self._handle_send_params(params)
                    self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": {"task": task}})
                    return
                if method in ("GetTask", "tasks/get"):
                    tid = str(params.get("id") or str(params.get("name", "")).split("/")[-1])
                    task = coord.get_task(tid)
                    self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": task})
                    return
                if method in ("ListTasks", "tasks/list"):
                    ctx_id = str(params.get("contextId") or "")
                    tasks = coord.list_tasks(agent=self.server.agent_name, context_id=ctx_id)
                    self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": {"tasks": tasks}})
                    return
                if method in ("CancelTask", "tasks/cancel"):
                    tid = str(params.get("id") or str(params.get("name", "")).split("/")[-1])
                    task = coord.cancel_task(tid)
                    self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": task})
                    return
                self._send_json(
                    200,
                    {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}},
                )
            except KeyError as e:
                self._send_json(
                    200,
                    {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32001, "message": str(e)}},
                )
            except Exception as e:
                self._send_json(
                    200,
                    {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": str(e)}},
                )
            return

        self._send_json(404, {"error": {"code": 404, "message": f"Unsupported POST path {path}"}})


def run_daemon() -> int:
    """Run both local A2A 1.0 Agent servers (:7778 antigravity, :7779 codex) in one process."""
    coord = TaskCoordinator()
    servers: list[ThreadedHTTPServer] = []
    for agent_name, cfg in AGENTS_CONFIG.items():
        srv = ThreadedHTTPServer((BIND_HOST, cfg["port"]), agent_name, coord)
        t = threading.Thread(target=srv.serve_forever, name=f"a2a-{agent_name}", daemon=True)
        t.start()
        servers.append(srv)
        print(f"[labflow-a2a] {agent_name} A2A 1.0 server listening on {cfg['url']}", flush=True)

    stop_ev = threading.Event()

    def _on_sig(signum: int, _frame: Any) -> None:
        stop_ev.set()

    signal.signal(signal.SIGINT, _on_sig)
    signal.signal(signal.SIGTERM, _on_sig)
    stop_ev.wait()
    for srv in servers:
        srv.shutdown()
    return 0


# ---------------------------------------------------------------------------
# MCP Stdio Server (`labflow-a2a mcp --self <antigravity|codex>`)
# ---------------------------------------------------------------------------


def http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 120.0) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "A2A-Version": "1.0"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} from {url}: {raw}") from e


def detect_self_session_id(self_agent: str) -> str:
    """Auto-detect the active session ID for the calling harness when `session='auto'`."""
    meta_raw = os.environ.get("ANTIGRAVITY_SOURCE_METADATA")
    if meta_raw:
        try:
            cid = json.loads(meta_raw).get("tool", {}).get("conversationId")
            if cid:
                return str(cid)
        except Exception:
            pass

    if self_agent == "antigravity":
        sessions = list_antigravity_sessions(limit=20)
        running = [s for s in sessions if s.get("status") == "CASCADE_RUN_STATUS_RUNNING"]
        if running:
            return running[0]["session_id"]
        return sessions[0]["session_id"] if sessions else ""

    if self_agent == "codex":
        cwd = os.getcwd()
        scoped = list_codex_sessions(cwd=cwd, limit=10)
        if scoped:
            return scoped[0]["session_id"]
        any_sess = list_codex_sessions(limit=5)
        return any_sess[0]["session_id"] if any_sess else ""

    return ""


MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "a2a_list_agents",
        "description": "List available A2A 1.0 workbench agents (antigravity, codex) and check their live health.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "a2a_list_sessions",
        "description": "List GUI conversations/sessions in `codex` or `antigravity` with their session_id (contextId), title, cwd, IRQ status, and pending inbox count.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": ["codex", "antigravity", "all"], "default": "all"},
                "query": {"type": "string", "description": "Optional substring filter on session title, UUID, or cwd."},
                "cwd": {"type": "string", "description": "Optional working directory filter."},
                "limit": {"type": "integer", "default": 15},
            },
        },
    },
    {
        "name": "a2a_send",
        "description": "Send an A2A 1.0 message to a specific session in `codex` or `antigravity` (or any A2A URL). For `codex`, automatically wakes open GUI chats or revives cold chats via `codex queue --resume` (pass session='new' to create a fresh chat). Never silently falls back to CLI for Antigravity App sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "'codex', 'antigravity', or a full http(s):// A2A agent URL."},
                "session": {
                    "type": "string",
                    "description": "Target session UUID (contextId), conversation title substring, 'latest' (default), or 'new' (Codex only).",
                    "default": "latest",
                },
                "text": {"type": "string", "description": "Message body to send."},
                "cwd": {"type": "string", "description": "Working directory filter (or directory for session='new')."},
                "blocking": {"type": "boolean", "default": True, "description": "Wait for the target session's reply."},
                "timeout_sec": {"type": "number", "default": 90, "description": "Max seconds to wait before returning WORKING task_id."},
            },
            "required": ["agent", "text"],
        },
    },
    {
        "name": "a2a_get_task",
        "description": "Fetch current A2A 1.0 Task state and reply artifacts by task_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "default": "codex", "description": "'codex', 'antigravity', or peer URL."},
                "task_id": {"type": "string"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "a2a_inbox",
        "description": "Read pending inbound A2A tasks addressed to this session (isolated per session_id so tabs never mix).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session": {
                    "type": "string",
                    "default": "auto",
                    "description": "'auto' (detect current GUI session), 'all' (all pending tasks for this app), or an explicit session UUID/title.",
                }
            },
        },
    },
    {
        "name": "a2a_reply",
        "description": "Complete an inbound A2A task with your reply text, immediately unblocking the waiting sender.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "text": {"type": "string", "description": "Reply content to return as an A2A Artifact."},
            },
            "required": ["task_id", "text"],
        },
    },
]


def resolve_agent_url(agent_or_url: str) -> str:
    key = agent_or_url.strip().lower()
    if key in AGENTS_CONFIG:
        return AGENTS_CONFIG[key]["url"]
    if agent_or_url.startswith("http://") or agent_or_url.startswith("https://"):
        return agent_or_url.rstrip("/")
    raise ValueError(f"Unknown agent {agent_or_url!r}; expected 'codex', 'antigravity', or http(s):// URL")


def handle_mcp_tool(self_agent: str, name: str, args: dict[str, Any]) -> Any:
    control_url = AGENTS_CONFIG["antigravity"]["url"]

    if name == "a2a_list_agents":
        out = []
        for ag_name, cfg in AGENTS_CONFIG.items():
            try:
                health = http_json("GET", f"{cfg['url']}/healthz", timeout=3.0)
                online = bool(health.get("ok"))
            except Exception:
                online = False
            out.append({"agent": ag_name, "url": cfg["url"], "online": online, "self": ag_name == self_agent})
        return out

    if name == "a2a_list_sessions":
        target = str(args.get("agent") or "all").lower()
        targets = ["codex", "antigravity"] if target == "all" else [target]
        qs_base = {
            "query": str(args.get("query") or ""),
            "cwd": str(args.get("cwd") or ""),
            "limit": str(int(args.get("limit") or 15)),
        }
        combined: list[dict[str, Any]] = []
        for t in targets:
            qs = urllib.parse.urlencode({**qs_base, "agent": t})
            res = http_json("GET", f"{control_url}/internal/sessions?{qs}", timeout=8.0)
            combined.extend(res.get("sessions", []))
        return combined

    if name == "a2a_send":
        target_spec = str(args["agent"])
        url = resolve_agent_url(target_spec)
        session = str(args.get("session") or "latest")
        text = str(args["text"])
        cwd = str(args.get("cwd") or "")
        blocking = bool(args.get("blocking", True))
        timeout_sec = float(args.get("timeout_sec", 90.0))
        self_sid = detect_self_session_id(self_agent)
        sender_label = f"{self_agent}:{self_sid[:8]}" if self_sid else self_agent

        rpc_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "contextId": session,
                    "role": "ROLE_USER",
                    "parts": [{"text": text}],
                    "metadata": {
                        "from": sender_label,
                        "fromAgent": self_agent,
                        "fromSessionId": self_sid,
                        "session": session,
                        "cwd": cwd,
                        "blocking": blocking,
                        "timeout_sec": timeout_sec,
                    },
                },
                "configuration": {"returnImmediately": not blocking},
            },
        }
        resp = http_json("POST", f"{url}/", payload=rpc_req, timeout=max(10.0, timeout_sec + 15.0))
        if "error" in resp:
            raise RuntimeError(resp["error"].get("message") or str(resp["error"]))
        return resp.get("result", {}).get("task", resp.get("result"))

    if name == "a2a_get_task":
        url = resolve_agent_url(str(args.get("agent") or "codex"))
        tid = str(args["task_id"])
        resp = http_json(
            "POST",
            f"{url}/",
            payload={"jsonrpc": "2.0", "id": 1, "method": "GetTask", "params": {"id": tid}},
            timeout=10.0,
        )
        if "error" in resp:
            raise RuntimeError(resp["error"].get("message") or str(resp["error"]))
        return resp.get("result")

    if name == "a2a_inbox":
        sess_arg = str(args.get("session") or "auto").strip()
        if sess_arg.lower() == "all":
            sid = ""
        elif sess_arg.lower() in ("auto", ""):
            sid = detect_self_session_id(self_agent)
        else:
            # Allow passing title or UUID
            sessions = (
                list_codex_sessions(query=sess_arg, limit=5)
                if self_agent == "codex"
                else list_antigravity_sessions(query=sess_arg, limit=5)
            )
            sid = sessions[0]["session_id"] if sessions else sess_arg
        qs = urllib.parse.urlencode({"agent": self_agent, "session_id": sid})
        res = http_json("GET", f"{control_url}/internal/inbox?{qs}", timeout=8.0)
        return {"self_agent": self_agent, "session_id": sid or "(all)", "inbox": res.get("inbox", [])}

    if name == "a2a_reply":
        res = http_json(
            "POST",
            f"{control_url}/internal/reply",
            payload={"task_id": str(args["task_id"]), "text": str(args["text"]), "responder": self_agent},
            timeout=10.0,
        )
        if "error" in res:
            raise RuntimeError(str(res["error"]))
        return res.get("task")

    raise ValueError(f"Unknown MCP tool: {name}")


def run_mcp(self_agent: str) -> int:
    """Run JSON-RPC 2.0 MCP server over stdio."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue

        method = msg.get("method", "")
        req_id = msg.get("id")
        # Notifications have no `id`
        if req_id is None:
            continue

        if method == "initialize":
            client_proto = (msg.get("params") or {}).get("protocolVersion") or "2024-11-05"
            reply = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": client_proto,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "labflow-a2a", "version": VERSION},
                },
            }
        elif method == "ping":
            reply = {"jsonrpc": "2.0", "id": req_id, "result": {}}
        elif method == "tools/list":
            reply = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
        elif method == "tools/call":
            params = msg.get("params") or {}
            tname = str(params.get("name") or "")
            targs = params.get("arguments") or {}
            try:
                out = handle_mcp_tool(self_agent, tname, targs)
                text_out = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, indent=2)
                reply = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": text_out}], "isError": False},
                }
            except Exception as e:
                reply = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True},
                }
        else:
            reply = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


# ---------------------------------------------------------------------------
# Race-Free Zero-CPU Interrupt Listener (`labflow-a2a wait-irq`)
# ---------------------------------------------------------------------------


IN_CLOEXEC = 0x00080000
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100


def run_wait_irq(agent: str, session_spec: str, timeout_sec: float) -> int:
    """Block with 0% CPU via Linux inotify until an inbound A2A task arrives for this session."""
    if session_spec in ("auto", ""):
        sid = detect_self_session_id(agent)
        if not sid:
            print("Error: could not auto-detect active session_id; pass --session <id|title>", file=sys.stderr)
            return 1
    else:
        sessions = list_antigravity_sessions(query=session_spec, limit=5) if agent == "antigravity" else list_codex_sessions(query=session_spec, limit=5)
        sid = sessions[0]["session_id"] if sessions else session_spec

    sdir = session_dir_for(agent, sid)
    armed_file = sdir / "armed.json"
    control_url = AGENTS_CONFIG["antigravity"]["url"]

    def fetch_pending() -> list[dict[str, Any]]:
        qs = urllib.parse.urlencode({"agent": agent, "session_id": sid})
        res = http_json("GET", f"{control_url}/internal/inbox?{qs}", timeout=5.0)
        return res.get("inbox", [])

    # Set up Linux inotify watch BEFORE checking pending inbox so zero events can slip in between.
    inotify_fd = -1
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        inotify_fd = libc.inotify_init1(IN_CLOEXEC)
        if inotify_fd >= 0:
            libc.inotify_add_watch(
                inotify_fd,
                str(sdir).encode("utf-8"),
                ctypes.c_uint32(IN_CLOSE_WRITE | IN_MOVED_TO | IN_CREATE),
            )

    atomic_write_json(armed_file, {"pid": os.getpid(), "session_id": sid, "armed_at": utc_now_iso()})

    def _cleanup(*_args: Any) -> None:
        armed_file.unlink(missing_ok=True)
        if inotify_fd >= 0:
            try:
                os.close(inotify_fd)
            except OSError:
                pass

    signal.signal(signal.SIGINT, lambda s, f: (_cleanup(), sys.exit(130)))
    signal.signal(signal.SIGTERM, lambda s, f: (_cleanup(), sys.exit(143)))

    try:
        # Immediate race-free pre-check
        pending = fetch_pending()
        if pending:
            print(json.dumps({"event": "inbound_task", "agent": agent, "session_id": sid, "inbox": pending}, ensure_ascii=False, indent=2))
            return 0

        deadline = (time.time() + timeout_sec) if timeout_sec > 0 else None
        while True:
            wait_s = None if deadline is None else max(0.0, deadline - time.time())
            if wait_s is not None and wait_s <= 0:
                print(json.dumps({"event": "timeout", "agent": agent, "session_id": sid}, ensure_ascii=False))
                return 0

            if inotify_fd >= 0:
                rlist, _, _ = select.select([inotify_fd], [], [], wait_s)
                if rlist:
                    try:
                        os.read(inotify_fd, 4096)
                    except OSError:
                        pass
            else:
                # Non-Linux fallback
                time.sleep(min(1.0, wait_s if wait_s is not None else 1.0))

            pending = fetch_pending()
            if pending:
                print(json.dumps({"event": "inbound_task", "agent": agent, "session_id": sid, "inbox": pending}, ensure_ascii=False, indent=2))
                return 0
    finally:
        _cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(prog="labflow-a2a", description="Labflow Session-Addressable A2A 1.0 Service")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("daemon", help="Run the local A2A 1.0 workbench daemon (:7778 antigravity, :7779 codex)")

    p_mcp = sub.add_parser("mcp", help="Run stdio MCP server")
    p_mcp.add_argument("--self", dest="self_agent", choices=["antigravity", "codex"], required=True)

    p_irq = sub.add_parser("wait-irq", help="Block with 0% CPU until an inbound A2A message arrives for this GUI session")
    p_irq.add_argument("--agent", choices=["antigravity", "codex"], default="antigravity")
    p_irq.add_argument("--session", default="auto", help="Session UUID, title substring, or 'auto'")
    p_irq.add_argument("--timeout", type=float, default=0.0, help="Optional timeout in seconds (0 = wait indefinitely)")

    sub.add_parser("version", help="Print version")

    args = parser.parse_args()
    if args.cmd == "version":
        print(f"labflow-a2a {VERSION}")
        return 0
    if args.cmd == "daemon":
        return run_daemon()
    if args.cmd == "mcp":
        return run_mcp(args.self_agent)
    if args.cmd == "wait-irq":
        return run_wait_irq(args.agent, args.session, args.timeout)
    return 2


if __name__ == "__main__":
    sys.exit(main())
