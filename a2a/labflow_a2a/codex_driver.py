"""Codex Desktop app-server driver (hot/cold/new state machine) and natural message formatting."""

from __future__ import annotations

import json
import os
import pathlib
import select
import subprocess
import threading
import time
from typing import Any

from .config import build_codex_env, find_codex_binary

# Inline full natural prose up to 12k chars directly in the Codex chat bubble so humans
# see clean cross-agent dialogue and Codex avoids an extra `a2a_inbox` round-trip.
INLINE_BODY_LIMIT = 12000


def format_natural_inbound_message(text: str, sender: str, task_id: str, session_id: str) -> str:
    """Format an inbound A2A message with natural prose first and a minimal reply footer."""
    body = text.strip()
    if len(body) <= INLINE_BODY_LIMIT:
        footer = (
            f"(via A2A from {sender} · 处理完成后请调用 `a2a_reply(task_id='{task_id}', text=...)` 回传结果)"
        )
        return f"{body}\n\n---\n{footer}"

    preview = body[:1000].rstrip() + "\n...(正文较长已截断)..."
    footer = (
        f"(via A2A from {sender} · 完整正文请调用 `a2a_inbox(session='{session_id}')` 读取，"
        f"完成后请调用 `a2a_reply(task_id='{task_id}', text=...)` 回传结果)"
    )
    return f"{preview}\n\n---\n{footer}"


def start_codex_app_server() -> tuple[subprocess.Popen[str], Any, Any]:
    """Spawn `codex app-server --stdio` with Codex Desktop identity and return (proc, send_rpc, wait_id)."""
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
    """Create a fresh Codex Desktop-compatible thread via `app-server --stdio`."""
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


def dispatch_to_codex(
    session_id: str,
    session_meta: dict[str, Any],
    task_id: str,
    sender: str,
    text: str,
) -> str:
    """Deliver a natural-language A2A message to a new, cold, or hot Codex Desktop session."""
    prompt = format_natural_inbound_message(text=text, sender=sender, task_id=task_id, session_id=session_id)

    new_proc: subprocess.Popen[str] | None = session_meta.pop("_new_proc", None)
    if new_proc is not None:
        drive_app_server_turn_async(new_proc, session_id, prompt)
        return "codex_new_session_started"

    # Probe `thread/resume`:
    #   - Succeeds -> thread is COLD; keep `app-server` open for the full turn.
    #   - Errors with `already has an active writer` -> thread is HOT in Codex Desktop; use `codex queue`.
    probe_proc: subprocess.Popen[str] | None = None
    try:
        probe_proc, send_rpc, wait_id = start_codex_app_server()
        send_rpc({"jsonrpc": "2.0", "id": 2, "method": "thread/resume", "params": {"threadId": session_id}})
        resume_resp = wait_id(2, timeout_s=12.0)
        if "error" not in resume_resp:
            drive_app_server_turn_async(probe_proc, session_id, prompt)
            probe_proc = None
            return "codex_cold_session_resumed"
        probe_proc.terminate()
        probe_proc.wait(timeout=2)
        probe_proc = None
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
