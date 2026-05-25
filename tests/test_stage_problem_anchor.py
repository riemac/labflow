import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins" / "labflow" / "hooks" / "stage_hook.py"
HUD = ROOT / "plugins" / "labflow" / "hooks" / "stage_hud.py"
IDEA_UPDATE = ROOT / "plugins" / "labflow" / "skills" / "stage-idea-refine" / "scripts" / "update_idea_state.py"
SCAFFOLD_UPDATE = ROOT / "plugins" / "labflow" / "skills" / "stage-design-scaffold" / "scripts" / "update_scaffold_state.py"


def run_hook(payload: dict, cwd: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=cwd,
        check=True,
    )
    output = json.loads(result.stdout)
    return output["hookSpecificOutput"]["additionalContext"]


def test_user_prompt_context_includes_problem_anchor_defaults(tmp_path: Path) -> None:
    context = run_hook(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "problem-anchor",
            "cwd": str(tmp_path),
            "prompt": "$labflow:stage-idea-refine",
        },
        cwd=tmp_path,
    )

    assert "problem_statement: <unset>" in context
    assert "problem_clarity: unknown." in context
    assert "Current problem anchor is unset or unclear" in context


def test_update_idea_state_can_update_problem_anchor(tmp_path: Path) -> None:
    run_hook(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "problem-anchor",
            "cwd": str(tmp_path),
            "prompt": "$labflow:stage-idea-refine",
        },
        cwd=tmp_path,
    )
    state_path = tmp_path / ".codex" / "labflow-stage" / "sessions" / "problem-anchor.json"

    subprocess.run(
        [
            sys.executable,
            str(IDEA_UPDATE),
            "--state-path",
            str(state_path),
            "--problem-statement",
            "Clarify HandCfg as a self-contained asset product.",
            "--problem-clarity",
            "framed",
            "--problem-note",
            "User agreed this is the current anchor.",
            "--exit-readiness",
            "candidate",
            "--idea-state",
            "Candidate route is to add a HandCfg-level runtime boundary.",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["problem_statement"] == "Clarify HandCfg as a self-contained asset product."
    assert state["problem_clarity"] == "framed"
    assert state["problem_statement_note"] == "User agreed this is the current anchor."
    assert state["problem_statement_updated_by"] == "agent"


def test_update_scaffold_state_can_update_problem_anchor(tmp_path: Path) -> None:
    run_hook(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "problem-anchor",
            "cwd": str(tmp_path),
            "prompt": "$labflow:stage-design-scaffold",
        },
        cwd=tmp_path,
    )
    state_path = tmp_path / ".codex" / "labflow-stage" / "sessions" / "problem-anchor.json"

    subprocess.run(
        [
            sys.executable,
            str(SCAFFOLD_UPDATE),
            "--state-path",
            str(state_path),
            "--problem-statement",
            "Preserve the HandCfg runtime boundary design.",
            "--problem-clarity",
            "stable",
            "--problem-note",
            "Ready to scaffold near code surfaces.",
            "--scaffold-readiness",
            "scaffolding",
            "--design-goal",
            "Write distributed prompts for the runtime boundary.",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["problem_statement"] == "Preserve the HandCfg runtime boundary design."
    assert state["problem_clarity"] == "stable"
    assert state["design_goal"] == "Write distributed prompts for the runtime boundary."


def test_hud_render_always_shows_problem_and_clarity() -> None:
    sys.path.insert(0, str(HUD.parent))
    try:
        import stage_hud

        rendered = stage_hud.render(
            {
                "stage_label": "idea-refine",
                "status": "active",
                "cwd": "/tmp/project",
                "entered_at": "2026-05-25T00:00:00Z",
                "updated_at": "2026-05-25T00:00:00Z",
            }
        )
    finally:
        sys.path.remove(str(HUD.parent))

    assert "problem : <unset>" in rendered
    assert "clarity : unknown" in rendered
