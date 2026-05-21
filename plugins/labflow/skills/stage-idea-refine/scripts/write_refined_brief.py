#!/usr/bin/env python3
"""Write a concise idea-refine brief after a ready_to_pass stage is passed."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def find_latest_passed_ready(cwd: Path) -> Path:
    candidates: list[tuple[str, Path]] = []
    for path in sorted((cwd / SESSIONS_DIR).glob("*.json")):
        if path.name.endswith(".hud.json"):
            continue
        state = read_json(path)
        if (
            state.get("stage") == "stage-idea-refine"
            and state.get("status") == "passed"
            and state.get("exit_readiness") == "ready_to_pass"
        ):
            candidates.append((str(state.get("updated_at") or ""), path))
    if not candidates:
        raise SystemExit("No passed ready_to_pass stage-idea-refine session found; pass --state-path.")
    return sorted(candidates)[-1][1]


def resolve_state_path(args: argparse.Namespace) -> Path:
    if args.state_path:
        return Path(args.state_path).expanduser().resolve()
    cwd = Path(args.cwd or os.getcwd()).expanduser().resolve()
    safe_id = safe_session_id(args.session_id)
    if safe_id:
        return cwd / SESSIONS_DIR / f"{safe_id}.json"
    return find_latest_passed_ready(cwd)


def default_brief_path(state_path: Path) -> Path:
    return state_path.with_suffix(".idea-refine.md")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-path", help="Exact passed session state path.")
    parser.add_argument("--cwd", help="Project root; defaults to current working directory.")
    parser.add_argument("--session-id", help="Codex session id if known.")
    parser.add_argument("--output", help="Optional output markdown path; defaults next to session json.")
    parser.add_argument("--allow-not-ready", action="store_true", help="Allow writing even if not passed ready_to_pass.")
    args = parser.parse_args(argv)

    state_path = resolve_state_path(args)
    state = read_json(state_path)
    if not args.allow_not_ready:
        if state.get("stage") != "stage-idea-refine" or state.get("status") != "passed":
            raise SystemExit("Brief should normally be written after stage-idea-refine has passed.")
        if state.get("exit_readiness") != "ready_to_pass":
            raise SystemExit("Brief should normally be written only for ready_to_pass stages.")

    content = sys.stdin.read().strip()
    if not content:
        raise SystemExit("Brief content must be provided on stdin.")

    output = Path(args.output).expanduser().resolve() if args.output else default_brief_path(state_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    header = "<!-- Labflow idea-refine brief; user-facing recall artifact, not auto-injected. -->\n"
    output.write_text(header + content + "\n", encoding="utf-8")

    now = utc_now()
    state["refined_brief_path"] = str(output)
    state["refined_brief_written_at"] = now
    state["updated_at"] = now
    write_json(state_path, state)
    print(json.dumps({"state_path": str(state_path), "refined_brief_path": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
