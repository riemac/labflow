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
    "stage-design-scaffold": {
        "label": "design-scaffold",
        "title": "Design Scaffold",
        "contract": (
            "We are in the design-scaffold stage. Externalize a mature design into distributed prompts: "
            "TODOs, docstrings, field documentation, interface shells, module notes, or design anchors. "
            "Do not implement full behavior unless the user explicitly exits or asks to implement."
        ),
    },
}

ENTER_RE = re.compile(
    r"(?<![\w./-])\$labflow:(stage-idea-refine|stage-goal-clarify|stage-design-scaffold)(?![\w./-])",
    re.IGNORECASE,
)
PASS_RE = re.compile(r"(?m)^\s*\$labflow:stage-control\s+pass\s*$", re.IGNORECASE)
CANCEL_RE = re.compile(r"(?m)^\s*\$labflow:stage-control\s+cancel\s*$", re.IGNORECASE)
STATUS_RE = re.compile(r"(?m)^\s*\$labflow:stage-control\s+status\s*$", re.IGNORECASE)
IDEA_READINESS_VALUES = {"vague", "not_ready", "candidate", "ready_to_pass"}
SCAFFOLD_READINESS_VALUES = {"mapping", "scaffolding", "reviewing", "ready_to_pass"}
PROBLEM_CLARITY_VALUES = {"unknown", "fuzzy", "framed", "stable"}

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
    if os.environ.get("LABFLOW_STAGE_HUD_DISABLED"):
        return
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


def format_list_for_context(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, str):
        return value.strip()
    return ""


def normalize_problem_clarity(value: Any) -> str:
    clarity = str(value or "unknown").strip()
    return clarity if clarity in PROBLEM_CLARITY_VALUES else "unknown"


def problem_summary(state: dict[str, Any]) -> tuple[str, str]:
    problem = str(state.get("problem_statement") or "").strip() or "<unset>"
    clarity = normalize_problem_clarity(state.get("problem_clarity"))
    return problem, clarity


def append_problem_guidance(lines: list[str], state: dict[str, Any]) -> None:
    problem, clarity = problem_summary(state)
    note = str(state.get("problem_statement_note") or "").strip()
    if note:
        lines.append(f"- problem_note: {note}")
    if problem == "<unset>" or clarity in {"unknown", "fuzzy"}:
        lines.append(
            "- Problem anchor is unset or unclear; clarify/update it only when the discussion state materially changes."
        )


def stage_context(state: dict[str, Any]) -> str:
    stage = str(state.get("stage"))
    spec = STAGES.get(stage, STAGES["stage-idea-refine"])
    problem, clarity = problem_summary(state)
    state_path = str(state.get("_state_path") or "")
    lines = [
        "[Labflow Stage Runtime]",
        f"stage: {spec['title']} (`{stage}`)",
        f"problem: {problem} (clarity={clarity})",
    ]
    if stage == "stage-idea-refine":
        readiness = str(state.get("exit_readiness") or "vague")
        idea_state = str(state.get("idea_state") or "").strip() or "<unset>"
        lines[1] = f"{lines[1]}, readiness={readiness}"
        lines.append(f"idea_state: {idea_state}")
        if state_path:
            lines.append(f"state_file: {state_path}")
        lines.append("")
        lines.append("guidance:")
        lines.append("- Stay in idea-refine discussion; do not implement unless the user exits or asks.")
        lines.append(
            "- Prefer short explanation + request_user_input for high-impact ambiguities; batch independent questions when useful."
        )
        lines.append("- Long systematic answers are for requested summaries, planning, or evidence consolidation.")
        append_problem_guidance(lines, state)
        lines.append("- Update problem/idea state only when discussion state materially changes.")
    elif stage == "stage-design-scaffold":
        readiness = str(state.get("scaffold_readiness") or "mapping")
        design_goal = str(state.get("design_goal") or "No design_goal recorded yet.")
        target_surfaces = state.get("target_surfaces") or []
        current_surface = str(state.get("current_surface") or "No current_surface recorded yet.")
        completed_surfaces = state.get("completed_surfaces") or []
        open_questions = state.get("open_questions") or []
        lines[1] = f"{lines[1]}, readiness={readiness}"
        lines.extend(
            [
                f"design_goal: {design_goal}",
                f"target_surfaces: {format_list_for_context(target_surfaces) or 'None recorded.'}",
                f"current_surface: {current_surface}",
                f"completed_surfaces: {format_list_for_context(completed_surfaces) or 'None recorded.'}",
                f"open_questions: {format_list_for_context(open_questions) or 'None recorded.'}",
            ]
        )
        stop_guard = str(state.get("last_stop_guard") or "").strip()
        if stop_guard:
            lines.append(f"last_stop_guard: {stop_guard}")
        if state_path:
            lines.append(f"state_file: {state_path}")
        lines.append("")
        lines.append("guidance:")
        lines.append("- Stay in design-scaffold mode; do not implement full behavior unless the user exits or asks.")
        lines.append("- Update scaffold state only when design goal, surfaces, completed work, or open questions materially change.")
        append_problem_guidance(lines, state)
    else:
        if state_path:
            lines.append(f"state_file: {state_path}")
        lines.append("")
        lines.append("guidance:")
        lines.append(f"- {spec['contract']}")
        append_problem_guidance(lines, state)
    lines.append("")
    lines.append("commands: $labflow:stage-control pass | cancel | status")
    return "\n".join(lines)


def start_stage(input_data: dict[str, Any], state_path: Path, stage: str) -> dict[str, Any]:
    now = utc_now()
    previous = read_state(state_path) or {}
    same_active_stage = previous.get("stage") == stage and previous.get("status") == "active"
    state = {
        "schema_version": 1,
        "status": "active",
        "stage": stage,
        "stage_label": STAGES[stage]["label"],
        "session_id": input_data.get("session_id"),
        "cwd": str(Path(input_data.get("cwd") or os.getcwd()).resolve()),
        "entered_at": previous.get("entered_at") if same_active_stage else now,
        "updated_at": now,
        "hud_backend": previous.get("hud_backend", "ghostty-window"),
    }
    state["problem_statement"] = previous.get("problem_statement") if same_active_stage else ""
    state["problem_clarity"] = previous.get("problem_clarity") if same_active_stage else "unknown"
    state["problem_clarity"] = normalize_problem_clarity(state["problem_clarity"])
    state["problem_statement_note"] = previous.get("problem_statement_note") if same_active_stage else ""
    state["problem_statement_updated_at"] = previous.get("problem_statement_updated_at") if same_active_stage else ""
    state["problem_statement_updated_by"] = previous.get("problem_statement_updated_by") if same_active_stage else ""
    if stage == "stage-idea-refine":
        state["exit_readiness"] = previous.get("exit_readiness") if same_active_stage else "vague"
        if state["exit_readiness"] not in IDEA_READINESS_VALUES:
            state["exit_readiness"] = "vague"
        state["idea_state"] = previous.get("idea_state") if same_active_stage else ""
        state["idea_state_updated_at"] = previous.get("idea_state_updated_at") if same_active_stage else ""
        state["idea_state_updated_by"] = previous.get("idea_state_updated_by") if same_active_stage else ""
        state["refined_brief_path"] = previous.get("refined_brief_path") if same_active_stage else ""
    elif stage == "stage-design-scaffold":
        state["scaffold_readiness"] = previous.get("scaffold_readiness") if same_active_stage else "mapping"
        if state["scaffold_readiness"] not in SCAFFOLD_READINESS_VALUES:
            state["scaffold_readiness"] = "mapping"
        state["design_goal"] = previous.get("design_goal") if same_active_stage else ""
        state["target_surfaces"] = previous.get("target_surfaces") if same_active_stage else []
        state["current_surface"] = previous.get("current_surface") if same_active_stage else ""
        state["completed_surfaces"] = previous.get("completed_surfaces") if same_active_stage else []
        state["open_questions"] = previous.get("open_questions") if same_active_stage else []
        state["scaffold_state_updated_at"] = previous.get("scaffold_state_updated_at") if same_active_stage else ""
        state["scaffold_state_updated_by"] = previous.get("scaffold_state_updated_by") if same_active_stage else ""
        state["scaffold_state_note"] = previous.get("scaffold_state_note") if same_active_stage else ""
        state["last_stop_guard"] = previous.get("last_stop_guard") if same_active_stage else ""
        state["last_stop_guard_at"] = previous.get("last_stop_guard_at") if same_active_stage else ""
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
        return "Labflow stage: inactive. Start with `$labflow:stage-idea-refine` or `$labflow:stage-goal-clarify`."
    stage = state.get("stage", "unknown")
    status = state.get("status", "unknown")
    entered = state.get("entered_at", "unknown")
    updated = state.get("updated_at", "unknown")
    parts = [f"Labflow stage: {status}", f"stage={stage}", f"entered_at={entered}", f"updated_at={updated}"]
    parts.append(f"problem_clarity={normalize_problem_clarity(state.get('problem_clarity'))}")
    problem = str(state.get("problem_statement") or "").strip()
    parts.append(f"problem_statement={problem or '<unset>'}")
    if stage == "stage-idea-refine":
        parts.append(f"exit_readiness={state.get('exit_readiness', 'vague')}")
        idea_state = str(state.get("idea_state") or "").strip()
        if idea_state:
            parts.append(f"idea_state={idea_state}")
        brief = str(state.get("refined_brief_path") or "").strip()
        if brief:
            parts.append(f"refined_brief_path={brief}")
    elif stage == "stage-design-scaffold":
        parts.append(f"scaffold_readiness={state.get('scaffold_readiness', 'mapping')}")
        design_goal = str(state.get("design_goal") or "").strip()
        if design_goal:
            parts.append(f"design_goal={design_goal}")
        current_surface = str(state.get("current_surface") or "").strip()
        if current_surface:
            parts.append(f"current_surface={current_surface}")
        completed = format_list_for_context(state.get("completed_surfaces") or [])
        if completed:
            parts.append(f"completed_surfaces={completed}")
    return "; ".join(parts) + "."


def handle_user_prompt(input_data: dict[str, Any], state_path: Path) -> None:
    prompt = str(input_data.get("prompt") or "")
    enter = ENTER_RE.search(prompt)
    if enter:
        state = start_stage(input_data, state_path, enter.group(1))
        state["_state_path"] = str(state_path)
        output_context(stage_context(state))
        return

    if PASS_RE.search(prompt) or NATURAL_PASS_RE.search(prompt):
        state = finish_stage(state_path, "passed")
        if state:
            lines = ["Labflow stage has been marked passed for this session. Continue normally unless the user starts a new stage."]
            if state.get("stage") == "stage-idea-refine" and state.get("exit_readiness") == "ready_to_pass":
                lines.append(
                    "The passed idea-refine stage was ready_to_pass; if useful, write a concise refined brief now for user recall."
                )
                lines.append(f"State file: {state_path}")
            output_context("\n".join(lines))
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
        state["_state_path"] = str(state_path)
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
    state = record_stop_heartbeat(input_data, state_path)
    message = str(input_data.get("last_assistant_message") or "")
    if PASS_RE.search(message):
        finish_stage(state_path, "passed")
    elif CANCEL_RE.search(message):
        finish_stage(state_path, "cancelled")
    elif state and state.get("stage") == "stage-design-scaffold":
        state["last_stop_guard"] = (
            "Previous assistant turn stopped while design-scaffold was still active. "
            "On the next user turn, check whether design_goal, target/current surface, "
            "completed surfaces, or open questions need a state update."
        )
        state["last_stop_guard_at"] = utc_now()
        write_state(state_path, state)
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
