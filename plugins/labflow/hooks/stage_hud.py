#!/usr/bin/env python3
"""Ghostty window HUD for Labflow stage state.

The HUD is intentionally best-effort: hook failures must never block Codex.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import textwrap
from pathlib import Path


HEARTBEAT_STALE_SECONDS = 3.0


def read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp.replace(path)


def hud_path(state_path: Path) -> Path:
    return state_path.with_suffix(".hud.json")


def is_process_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def hud_alive(path: Path) -> bool:
    hud = read_json(path)
    pid = hud.get("pid")
    if not isinstance(pid, int) or not is_process_alive(pid):
        return False
    heartbeat = hud.get("heartbeat_at")
    if not isinstance(heartbeat, (int, float)):
        return True
    return (time.time() - float(heartbeat)) <= HEARTBEAT_STALE_SECONDS


def render(state: dict) -> str:
    status = state.get("status", "inactive")
    stage = state.get("stage_label") or state.get("stage", "none")
    cwd = state.get("cwd", "")
    entered = state.get("entered_at", "")
    updated = state.get("updated_at", "")
    readiness = state.get("exit_readiness")
    idea_state = str(state.get("idea_state") or "").strip()
    brief_path = str(state.get("refined_brief_path") or "").strip()
    last_stop = state.get("last_stop_hook_at", "never")
    stop_count = state.get("stop_hook_count", 0)
    turn_id = state.get("last_stop_turn_id") or "none"
    lines = [
        "Labflow Stage HUD",
        "=================",
        f"stage   : {stage}",
        f"status  : {status}",
        f"cwd     : {cwd}",
        f"entered : {entered}",
        f"updated : {updated}",
    ]
    if readiness:
        lines.append(f"ready   : {readiness}")
    if idea_state:
        wrapped = textwrap.wrap(idea_state, width=72)
        if wrapped:
            lines.append(f"idea    : {wrapped[0]}")
            lines.extend(f"          {line}" for line in wrapped[1:4])
            if len(wrapped) > 4:
                lines.append("          ...")
    if brief_path:
        lines.append(f"brief   : {brief_path}")
    lines.extend(
        [
            f"stop    : count={stop_count} | last={last_stop}",
            f"turn    : {turn_id}",
            "",
            "commands: $stage-pass | $stage-cancel | $stage-status",
            "note    : closing this window does not finish the stage",
        ]
    )
    return "\n".join(lines)


def watch(state_path: Path) -> int:
    hud_state_path = hud_path(state_path)
    write_json(
        hud_state_path,
        {
            "backend": "ghostty-window",
            "pid": os.getpid(),
            "started_at": time.time(),
            "heartbeat_at": time.time(),
            "state_path": str(state_path),
        },
    )
    try:
        while True:
            state = read_json(state_path)
            write_json(
                hud_state_path,
                {
                    "backend": "ghostty-window",
                    "pid": os.getpid(),
                    "started_at": read_json(hud_state_path).get("started_at", time.time()),
                    "heartbeat_at": time.time(),
                    "state_path": str(state_path),
                },
            )
            print("\033[2J\033[H", end="")
            print(render(state), flush=True)
            if state.get("status") != "active":
                time.sleep(0.8)
                return 0
            time.sleep(1.0)
    finally:
        current = read_json(hud_state_path)
        if current.get("pid") == os.getpid():
            current["pid"] = None
            current["heartbeat_at"] = time.time()
            write_json(hud_state_path, current)


def ghostty_command(state_path: Path, cwd: Path) -> list[str]:
    script = Path(__file__).resolve()
    return [
        "ghostty",
        "+new-window",
        f"--working-directory={cwd}",
        "--title=Labflow Stage HUD",
        "-e",
        "python3",
        str(script),
        "watch",
        str(state_path.resolve()),
    ]


def ensure(state_path: Path) -> int:
    state = read_json(state_path)
    if state.get("status") != "active":
        return 0
    hud_state_path = hud_path(state_path)
    if hud_alive(hud_state_path):
        return 0
    if shutil.which("ghostty") is None:
        return 0

    cwd = Path(str(state.get("cwd") or state_path.parent.parent.parent)).expanduser().resolve()
    command = ghostty_command(state_path, cwd)
    if os.environ.get("LABFLOW_STAGE_HUD_DRY_RUN"):
        dry_run = read_json(hud_state_path)
        dry_run.update({"backend": "ghostty-window", "dry_run_command": command, "dry_run_at": time.time()})
        write_json(hud_state_path, dry_run)
        return 0

    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        return 0
    return 0


def stop(state_path: Path) -> int:
    hud_state_path = hud_path(state_path)
    hud = read_json(hud_state_path)
    if hud:
        hud["stop_requested_at"] = time.time()
        write_json(hud_state_path, hud)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"ensure", "stop", "watch"}:
        print("Usage: stage_hud.py {ensure|stop|watch} <state.json>", file=sys.stderr)
        return 2
    action = argv[1]
    state_path = Path(argv[2]).resolve()
    if action == "ensure":
        return ensure(state_path)
    if action == "stop":
        return stop(state_path)
    return watch(state_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
