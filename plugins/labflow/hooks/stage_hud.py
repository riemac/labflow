#!/usr/bin/env python3
"""Small tmux HUD for Labflow stage state."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def read_state(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp.replace(path)


def tmux_available() -> bool:
    return bool(os.environ.get("TMUX")) and shutil.which("tmux") is not None


def pane_alive(pane_id: str | None) -> bool:
    if not pane_id or not tmux_available():
        return False
    result = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane_id, "#{pane_id}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def render(state: dict) -> str:
    status = state.get("status", "inactive")
    stage = state.get("stage_label") or state.get("stage", "none")
    cwd = state.get("cwd", "")
    entered = state.get("entered_at", "")
    lines = [
        "Labflow Stage HUD",
        f"stage: {stage} | status: {status}",
        f"cwd: {cwd}",
        f"entered: {entered}",
        "commands: $stage-pass | $stage-cancel | $stage-status",
    ]
    return "\n".join(lines)


def watch(state_path: Path) -> int:
    while True:
        state = read_state(state_path)
        print("\033[2J\033[H", end="")
        print(render(state), flush=True)
        if state.get("status") != "active":
            time.sleep(0.8)
            return 0
        time.sleep(1.0)


def ensure(state_path: Path) -> int:
    if not tmux_available():
        return 0
    state = read_state(state_path)
    if state.get("status") != "active":
        return 0
    if pane_alive(state.get("hud_pane_id")):
        return 0

    script = Path(__file__).resolve()
    command = f"python3 {script} watch {state_path.resolve()}"
    result = subprocess.run(
        ["tmux", "split-window", "-v", "-l", "6", "-d", "-P", "-F", "#{pane_id}", command],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        pane_id = result.stdout.strip()
        if pane_id:
            state["hud_pane_id"] = pane_id
            write_state(state_path, state)
    return 0


def stop(state_path: Path) -> int:
    state = read_state(state_path)
    pane_id = state.get("hud_pane_id")
    if pane_alive(pane_id):
        subprocess.run(["tmux", "kill-pane", "-t", pane_id], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if state:
        state["hud_pane_id"] = None
        write_state(state_path, state)
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
