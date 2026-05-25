#!/usr/bin/env python3
"""Update idea-refine stage state for the current Labflow session.

This script is intentionally standard-library only. It edits the session state
file that the Labflow stage hook owns; it does not infer research semantics.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READINESS_VALUES = {"vague", "not_ready", "candidate", "ready_to_pass"}
PROBLEM_CLARITY_VALUES = {"unknown", "fuzzy", "framed", "stable"}
SESSIONS_DIR = Path(".codex") / "labflow-stage" / "sessions"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_session_id(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", value.strip())
    return safe[:120] or None


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    tmp.replace(path)


def session_path(cwd: Path, session_id: str | None) -> Path | None:
    safe_id = safe_session_id(session_id)
    if safe_id:
        return cwd / SESSIONS_DIR / f"{safe_id}.json"
    return None


def find_active_state(cwd: Path) -> Path:
    active: list[Path] = []
    for path in sorted((cwd / SESSIONS_DIR).glob("*.json")):
        if path.name.endswith(".hud.json"):
            continue
        state = read_json(path)
        if state.get("status") == "active" and state.get("stage") == "stage-idea-refine":
            active.append(path)
    if len(active) == 1:
        return active[0]
    if not active:
        raise SystemExit("No active stage-idea-refine session state found; pass --state-path or --session-id.")
    raise SystemExit("Multiple active stage-idea-refine sessions found; pass --state-path or --session-id.")


def resolve_state_path(args: argparse.Namespace) -> Path:
    if args.state_path:
        return Path(args.state_path).expanduser().resolve()
    cwd = Path(args.cwd or os.getcwd()).expanduser().resolve()
    path = session_path(cwd, args.session_id)
    if path:
        return path
    return find_active_state(cwd)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-path", help="Exact .codex/labflow-stage/sessions/<session>.json path from hook context.")
    parser.add_argument("--cwd", help="Project root; defaults to current working directory.")
    parser.add_argument("--session-id", help="Codex session id if known.")
    parser.add_argument("--problem-statement", help="Current-best statement of the problem or goal anchoring this stage.")
    parser.add_argument("--problem-clarity", choices=sorted(PROBLEM_CLARITY_VALUES), help="How clear the problem anchor is.")
    parser.add_argument("--problem-note", help="Optional short reason for updating the problem anchor.")
    parser.add_argument("--exit-readiness", choices=sorted(READINESS_VALUES), required=True)
    parser.add_argument("--idea-state", required=True, help="Free-text summary of the current research idea state.")
    parser.add_argument("--note", default="", help="Optional short reason for this state update.")
    args = parser.parse_args(argv)

    state_path = resolve_state_path(args)
    state = read_json(state_path)
    if state.get("status") != "active" or state.get("stage") != "stage-idea-refine":
        raise SystemExit(f"State is not an active stage-idea-refine session: {state_path}")

    now = utc_now()
    problem_changed = any(
        value is not None
        for value in (args.problem_statement, args.problem_clarity, args.problem_note)
    )
    if args.problem_statement is not None:
        state["problem_statement"] = args.problem_statement.strip()
    if args.problem_clarity is not None:
        state["problem_clarity"] = args.problem_clarity
    elif "problem_clarity" not in state:
        state["problem_clarity"] = "unknown"
    if args.problem_note is not None:
        state["problem_statement_note"] = args.problem_note.strip()
    if problem_changed:
        state["problem_statement_updated_at"] = now
        state["problem_statement_updated_by"] = "agent"
    state["exit_readiness"] = args.exit_readiness
    state["idea_state"] = args.idea_state.strip()
    state["idea_state_note"] = args.note.strip()
    state["idea_state_updated_at"] = now
    state["idea_state_updated_by"] = "agent"
    state["updated_at"] = now
    write_json(state_path, state)
    print(json.dumps({"state_path": str(state_path), "exit_readiness": args.exit_readiness}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
