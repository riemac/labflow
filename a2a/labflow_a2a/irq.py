"""Race-free zero-CPU Linux inotify interrupt blocker (`labflow-a2a wait-irq`)."""

from __future__ import annotations

import ctypes
import json
import os
import select
import signal
import sys
import time
import urllib.parse
from typing import Any

from .config import AGENTS_CONFIG, atomic_write_json, session_dir_for, utc_now_iso
from .mcp_server import http_json
from .sessions import detect_self_session_id, list_antigravity_sessions, list_codex_sessions

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
        sessions = (
            list_antigravity_sessions(query=session_spec, limit=5)
            if agent == "antigravity"
            else list_codex_sessions(query=session_spec, limit=5)
        )
        sid = sessions[0]["session_id"] if sessions else session_spec

    sdir = session_dir_for(agent, sid)
    armed_file = sdir / "armed.json"
    control_url = AGENTS_CONFIG["antigravity"]["url"]

    def fetch_pending() -> list[dict[str, Any]]:
        qs = urllib.parse.urlencode({"agent": agent, "session_id": sid})
        return http_json("GET", f"{control_url}/internal/inbox?{qs}", timeout=5.0).get("inbox", [])

    # Arm inotify BEFORE checking pending inbox so no arrival can slip through the window.
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

    signal.signal(signal.SIGINT, lambda _s, _f: (_cleanup(), sys.exit(130)))
    signal.signal(signal.SIGTERM, lambda _s, _f: (_cleanup(), sys.exit(143)))

    try:
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
                time.sleep(min(1.0, wait_s if wait_s is not None else 1.0))

            pending = fetch_pending()
            if pending:
                print(json.dumps({"event": "inbound_task", "agent": agent, "session_id": sid, "inbox": pending}, ensure_ascii=False, indent=2))
                return 0
    finally:
        _cleanup()
