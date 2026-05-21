#!/usr/bin/env python3
"""Lightweight Stage-Driven Development hook runtime for Labflow.

The authoritative state lives in the active project's `.codex/` directory so
the user can inspect and delete it without knowing Codex's plugin data layout.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STAGE_DIR = Path(".codex") / "labflow-stage"
LEGACY_STATE_FILE = STAGE_DIR / "state.json"
SESSIONS_DIR = STAGE_DIR / "sessions"


STAGES = {
    "stage-idea-refine": {
        "label": "idea-refine",
        "title": "Idea Refine",
        "contract": (
            "We are in the idea-refine stage. Stay in discussion mode: clarify the research idea, "
            "surface assumptions, counterexamples, feasibility risks, evidence needs, and technical routes. "
            "Do not move into implementation unless the user explicitly exits or asks to implement."
        ),
    },
    "stage-goal-clarify": {
        "label": "goal-clarify",
        "title": "Goal Clarify",
        "contract": (
            "We are in the goal-clarify stage. Lock down success criteria, scope boundaries, non-goals, "
            "acceptance checks, required evidence, and risky tradeoffs before planning or implementation."
        ),
    },
}

ENTER_RE = re.compile(r"(?:\$|使用\s+|use\s+)?(stage-idea-refine|stage-goal-clarify)\b", re.IGNORECASE)
PASS_RE = re.compile(r"(?m)^\s*\$stage-pass\s*$")
CANCEL_RE = re.compile(r"(?m)^\s*\$stage-cancel\s*$")
STATUS_RE = re.compile(r"(?m)^\s*\$stage-status\s*$")

NATURAL_PASS_RE = re.compile(
    r"(?:这个阶段|stage|阶段).{0,8}(?:过了|通过|完成|结束|退出)",
    re.IGNORECASE,
)
NATURAL_CANCEL_RE = re.compile(r"(?:取消|放弃).{0,8}(?:stage|阶段)", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_input() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def safe_session_id(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", value.strip())
    return safe[:120] or None


def project_state_path(cwd: str | None, session_id: Any = None) -> Path:
    base = Path(cwd or os.getcwd()).resolve()
    safe_id = safe_session_id(session_id)
    if safe_id:
        return base / SESSIONS_DIR / f"{safe_id}.json"
    return base / LEGACY_STATE_FILE


def read_state(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else None
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp.replace(path)


def active_state(path: Path) -> dict[str, Any] | None:
    state = read_state(path)
    if state and state.get("status") == "active" and state.get("stage") in STAGES:
        return state
    return None


def project_root_from_state(state_path: Path) -> Path:
    state = read_state(state_path) or {}
    cwd = state.get("cwd")
    if isinstance(cwd, str) and cwd:
        return Path(cwd).expanduser().resolve()
    if state_path.parent.name == "sessions":
        return state_path.parents[3]
    return state_path.parents[2]


def run_hud(action: str, state_path: Path) -> None:
    script = Path(__file__).with_name("stage_hud.py")
    if not script.exists():
        return
    try:
        subprocess.run(
            ["python3", str(script), action, str(state_path)],
            cwd=str(project_root_from_state(state_path)),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.5,
            check=False,
        )
    except Exception:
        return


def output_context(text: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": text,
                }
            },
            ensure_ascii=False,
        )
    )


def stage_context(state: dict[str, Any]) -> str:
    stage = str(state.get("stage"))
    spec = STAGES.get(stage, STAGES["stage-idea-refine"])
    return "\n".join(
        [
            "[Labflow Stage Runtime]",
            f"Active stage: {spec['title']} (`{stage}`).",
            spec["contract"],
            "Use repo/code/document inspection for discoverable facts before asking the user.",
            "For high-impact human preferences or tradeoffs, ask one focused question instead of guessing.",
            "If the stage is clearly complete, either ask the user to send `$stage-pass` or include a standalone `$stage-pass` line.",
            "User commands: `$stage-pass`, `$stage-cancel`, `$stage-status`.",
        ]
    )


def start_stage(input_data: dict[str, Any], state_path: Path, stage: str) -> dict[str, Any]:
    now = utc_now()
    previous = read_state(state_path) or {}
    state = {
        "schema_version": 1,
        "status": "active",
        "stage": stage,
        "stage_label": STAGES[stage]["label"],
        "session_id": input_data.get("session_id"),
        "cwd": str(Path(input_data.get("cwd") or os.getcwd()).resolve()),
        "entered_at": previous.get("entered_at") if previous.get("stage") == stage else now,
        "updated_at": now,
        "hud_backend": previous.get("hud_backend", "ghostty-window"),
    }
    write_state(state_path, state)
    run_hud("ensure", state_path)
    return read_state(state_path) or state


def finish_stage(state_path: Path, status: str) -> dict[str, Any] | None:
    state = active_state(state_path)
    if not state:
        return None
    state["status"] = status
    state["updated_at"] = utc_now()
    write_state(state_path, state)
    run_hud("stop", state_path)
    return state


def summarize_status(state_path: Path) -> str:
    state = read_state(state_path)
    if not state:
        return "Labflow stage: inactive. Start with `$stage-idea-refine` or `$stage-goal-clarify`."
    stage = state.get("stage", "unknown")
    status = state.get("status", "unknown")
    entered = state.get("entered_at", "unknown")
    updated = state.get("updated_at", "unknown")
    return f"Labflow stage: {status}; stage={stage}; entered_at={entered}; updated_at={updated}."


def handle_user_prompt(input_data: dict[str, Any], state_path: Path) -> None:
    prompt = str(input_data.get("prompt") or "")
    enter = ENTER_RE.search(prompt)
    if enter:
        state = start_stage(input_data, state_path, enter.group(1))
        output_context(stage_context(state))
        return

    if PASS_RE.search(prompt) or NATURAL_PASS_RE.search(prompt):
        state = finish_stage(state_path, "passed")
        if state:
            output_context("Labflow stage has been marked passed for this session. Continue normally unless the user starts a new stage.")
        else:
            output_context("No active Labflow stage in this session.")
        return

    if CANCEL_RE.search(prompt) or NATURAL_CANCEL_RE.search(prompt):
        state = finish_stage(state_path, "cancelled")
        if state:
            output_context("Labflow stage has been cancelled for this session. Continue normally unless the user starts a new stage.")
        else:
            output_context("No active Labflow stage in this session.")
        return

    if STATUS_RE.search(prompt):
        output_context(summarize_status(state_path))
        return

    state = active_state(state_path)
    if state:
        output_context(stage_context(state))


def record_stop_heartbeat(input_data: dict[str, Any], state_path: Path) -> dict[str, Any] | None:
    state = active_state(state_path)
    if not state:
        return None
    state["last_stop_hook_at"] = utc_now()
    state["last_stop_turn_id"] = input_data.get("turn_id")
    state["stop_hook_count"] = int(state.get("stop_hook_count") or 0) + 1
    write_state(state_path, state)
    return state


def handle_stop(input_data: dict[str, Any], state_path: Path) -> None:
    record_stop_heartbeat(input_data, state_path)
    message = str(input_data.get("last_assistant_message") or "")
    if PASS_RE.search(message):
        finish_stage(state_path, "passed")
    elif CANCEL_RE.search(message):
        finish_stage(state_path, "cancelled")
    # Deliberately do not return decision:block. Stop must not push an extra turn
    # unless the user later opts into a stronger guard.


def main() -> int:
    input_data = read_input()
    state_path = project_state_path(input_data.get("cwd"), input_data.get("session_id"))
    event = input_data.get("hook_event_name")
    if event == "UserPromptSubmit":
        handle_user_prompt(input_data, state_path)
    elif event == "Stop":
        handle_stop(input_data, state_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
