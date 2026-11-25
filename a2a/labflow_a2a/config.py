"""Configuration, host-local state helpers, atomic JSON I/O, and Codex binary/env resolution."""

from __future__ import annotations

import datetime as dt
import glob
import json
import os
import pathlib
import tempfile
from typing import Any

from . import VERSION

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
    """Return True if a local OS process with `pid` currently exists."""
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


def find_codex_binary(prefer_desktop: bool = False) -> str:
    """Locate an installed Codex executable across PATH, ~/.nvm, and Desktop bundle."""
    desktop_bin = "/usr/lib/chatgpt/resources/codex"
    candidates: list[str] = []
    if prefer_desktop:
        candidates.append(desktop_bin)
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
    """Ensure NVM node bin directories are on PATH (required under systemd --user)."""
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


__all__ = [
    "AGENTS_CONFIG",
    "ANTIGRAVITY_PORT",
    "BIND_HOST",
    "CODEX_PORT",
    "VERSION",
    "atomic_write_json",
    "build_codex_env",
    "check_irq_armed",
    "find_codex_binary",
    "is_pid_alive",
    "session_dir_for",
    "state_root",
    "utc_now_iso",
]
