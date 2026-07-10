"""Human-first dossier setup and atomically maintained worker state."""

from __future__ import annotations

from datetime import UTC, datetime
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .models import clean_text


class DossierError(ValueError):
    """Raised for missing, unsafe, or conflicting dossier state."""


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def resolve_dossier(value: str | Path, *, require: bool = True) -> Path:
    raw = str(value)
    if not raw or "\x00" in raw:
        raise DossierError("dossier path is invalid")
    dossier = Path(raw).expanduser().resolve()
    if require and (not dossier.is_dir() or not (dossier / ".state").is_dir()):
        raise DossierError(f"not an initialized dossier: {dossier}")
    return dossier


def cache_path(dossier: Path) -> Path:
    return dossier / ".state" / "literature-cache.sqlite"


def _frontmatter(title: str, question: str | None, *, kind: str) -> str:
    # JSON string literals are valid, conservative YAML scalar values.
    today = datetime.now(UTC).date().isoformat()
    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"kind: {json.dumps(kind)}",
        'status: "active"',
        f"updated: {today}",
        f"search_cutoff: {today}",
    ]
    if question:
        lines.append(f"question: {json.dumps(question, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def initialize_dossier(
    path: str | Path, title: str, question: str | None = None, *, force: bool = False
) -> Path:
    """Create or conservatively repair a skeleton without erasing evidence."""
    dossier = resolve_dossier(path, require=False)
    title = clean_text(title, limit=500)
    question = clean_text(question, limit=4_000) or None
    if not title:
        raise DossierError("title must not be empty")
    frontmatter = _frontmatter(title, question, kind="literature-forensics-dossier")
    question_text = question or "State the bounded research question before delegation."
    files = {
        "README.md": (
            f"{frontmatter}\n\n# {title}\n\n"
            "This dossier is the durable, human-readable research record. Task sessions and the local cache are supporting state, not the source of truth.\n\n"
            f"## Research Question\n\n{question_text}\n\n"
            "## Current Bounded Answer\n\nNot synthesized yet.\n\n"
            "## Topic Lanes\n\n| Lane | Stage | Current finding | Artifact |\n| --- | --- | --- | --- |\n"
            "| _Unassigned_ | framing | Define lanes after the research brief is confirmed. | [brief](brief.md) |\n\n"
            "## Lead Verification Queue\n\n- No papers selected yet.\n\n"
            "## Next Checkpoint\n\n- Confirm the brief, scope, seeds, and search budget before delegation.\n\n"
            "## Navigation\n\n- [Research brief](brief.md)\n- [Curated literature map](MAP.md)\n- [Search log](search-log.md)\n- [Bibliography](bibliography.bib)\n- [Topic lanes](topics/)\n- [Paper cards and local PDFs](papers/)\n"
        ),
        "brief.md": (
            f"{_frontmatter(title, question, kind='research-brief')}\n\n# Research Brief\n\n"
            f"## Decision To Support\n\nDescribe the decision this investigation must make easier.\n\n"
            f"## Research Question\n\n{question_text}\n\n"
            "## Research Hunch\n\n| Field | Current definition |\n| --- | --- |\n"
            "| Phenomenon | |\n| Candidate mechanism | |\n| Setting | |\n| Intervention | |\n| Novelty axis | |\n| Counter-hypothesis | |\n\n"
            "## Search Semantics\n\n- Exact terms:\n- Mechanism aliases:\n- Setting aliases:\n- Intervention aliases:\n\n"
            "## Scope\n\n- In scope:\n- Out of scope:\n- Allowed local files/directories:\n\n"
            "## Seed Papers\n\n- \n\n"
            "## Budget And Stop Rule\n\n- Metadata candidates per lane:\n- Abstract screens per lane:\n- Targeted/full reads per lane:\n- Citation expansion: one hop per approved round.\n- Stop when:\n\n"
            "## Checkpoints And Decisions\n\n- Confirm framing before delegation.\n"
        ),
        "MAP.md": (
            f"{_frontmatter(title, question, kind='curated-literature-map')}\n\n# Literature MAP\n\n"
            f"## Research Question\n\n{question_text}\n\n## Graph\n\n"
            "```mermaid\nflowchart TD\n"
            '  Q000["<b>Q000 Research question</b>"]\n'
            '  T100["<b>T100 Topic lanes</b>"]\n'
            '  E200["<b>E200 Screened evidence</b>"]\n'
            '  G300["<b>G300 Candidate gap</b>"]\n'
            "  Q000 -->|decompose| T100\n  T100 -->|screen and verify| E200\n  E200 -->|bounded synthesis| G300\n\n"
            "  classDef question fill:#d9eaf7,stroke:#2f6f9f,stroke-width:2px,color:#111;\n"
            "  classDef evidence fill:#d8f5d0,stroke:#3a7a2a,stroke-width:2px,color:#111;\n"
            "  classDef gap fill:#d9d2e9,stroke:#674ea7,stroke-width:2px,color:#111;\n"
            "  class Q000 question;\n  class E200 evidence;\n  class G300 gap;\n```\n\n"
            "## Node Index\n\n| Node | Artifact | Class | Evidence depth | Meaning |\n| --- | --- | --- | --- | --- |\n"
            "| Q000 | [brief](brief.md) | question | framed | Replace with the confirmed question. |\n\n"
            "## Evidence Diagnosis\n\nNot synthesized yet.\n\n"
            "## Novelty Boundary\n\nNo bounded novelty inference yet.\n\n"
            "## Candidate Next Searches\n\n- Confirm topic lanes after the brief is reviewed.\n"
        ),
        "search-log.md": "# Search Log\n\n| Date | Query | Sources | Results | Notes |\n| --- | --- | --- | ---: | --- |\n",
        "bibliography.bib": "",
        "topics/README.md": "# Topic Lanes\n\nEach lane is maintained by one worker and written for human review.\n",
        "papers/README.md": "# Paper Evidence\n\nKeep `<citekey>.md` and the ignored local `<citekey>.pdf` beside each other.\n",
        ".gitignore": ".state/\npapers/*.pdf\n",
        ".state/workers.json": '{"version":1,"workers":[]}\n',
    }
    directories = ("topics", "papers", ".state")
    expected = [dossier / name for name in directories] + [
        dossier / name for name in files
    ]
    conflicts = [item for item in expected if item.exists()]
    state = dossier / ".state"
    papers = dossier / "papers"
    has_pdfs = papers.is_dir() and any(papers.rglob("*.pdf"))
    has_cache_files = state.is_dir() and any(state.glob("literature-cache.sqlite*"))
    if (has_cache_files or has_pdfs) and conflicts:
        raise DossierError(
            "dossier contains cached evidence or PDFs; init never resets existing evidence"
        )
    if conflicts and not force:
        display = ", ".join(str(item.relative_to(dossier)) for item in conflicts)
        raise DossierError(
            f"dossier skeleton already exists ({display}); use --force only to repair unchanged files"
        )
    if force:
        changed = []
        for relative, content in files.items():
            target = dossier / relative
            if target.exists() and target.read_text(encoding="utf-8") != content:
                changed.append(relative)
        if changed:
            raise DossierError(
                "refusing to overwrite changed skeleton files: " + ", ".join(changed)
            )
    dossier.mkdir(parents=True, exist_ok=True)
    for name in directories:
        (dossier / name).mkdir(exist_ok=True)
    for relative, content in files.items():
        target = dossier / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(content, encoding="utf-8")
    return dossier


def _worker_path(dossier: Path) -> Path:
    return dossier / ".state" / "workers.json"


@contextmanager
def _worker_lock(dossier: Path):
    """Serialize read-modify-write updates across local worker processes."""
    lock_path = dossier / ".state" / "workers.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    serialized = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _load_workers(dossier: Path) -> dict[str, Any]:
    path = _worker_path(dossier)
    if not path.exists():
        return {"version": 1, "workers": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DossierError(f"invalid worker registry: {error}") from error
    if (
        not isinstance(payload, dict)
        or payload.get("version") != 1
        or not isinstance(payload.get("workers"), list)
    ):
        raise DossierError("invalid worker registry format")
    return payload


def _worker_value(value: str, name: str, *, limit: int = 500) -> str:
    cleaned = clean_text(value, limit=limit)
    if not cleaned:
        raise DossierError(f"{name} must not be empty")
    return cleaned


def _artifact_value(value: str | None) -> str | None:
    if value is None:
        return None
    artifact = _worker_value(value, "artifact", limit=1_000)
    candidate = Path(artifact)
    if candidate.is_absolute() or ".." in candidate.parts or "\x00" in artifact:
        raise DossierError("artifact must be a relative dossier path")
    return candidate.as_posix()


def set_worker(
    dossier: Path, *, lane: str, task_id: str, phase: str, artifact: str | None = None
) -> dict[str, Any]:
    worker = {
        "artifact": _artifact_value(artifact),
        "lane": _worker_value(lane, "lane"),
        "last_used": _timestamp(),
        "phase": _worker_value(phase, "phase"),
        "task_id": _worker_value(task_id, "task_id"),
    }
    with _worker_lock(dossier):
        payload = _load_workers(dossier)
        workers = [
            item
            for item in payload["workers"]
            if isinstance(item, dict) and item.get("task_id") != worker["task_id"]
        ]
        workers.append(worker)
        payload["workers"] = sorted(
            workers,
            key=lambda item: (str(item.get("lane", "")), str(item.get("task_id", ""))),
        )
        _atomic_json_write(_worker_path(dossier), payload)
    return worker


def list_workers(dossier: Path) -> list[dict[str, Any]]:
    payload = _load_workers(dossier)
    return sorted(
        (item for item in payload["workers"] if isinstance(item, dict)),
        key=lambda item: (str(item.get("lane", "")), str(item.get("task_id", ""))),
    )


def archive_worker(dossier: Path, *, task_id: str) -> dict[str, Any]:
    task_id = _worker_value(task_id, "task_id")
    with _worker_lock(dossier):
        workers = list_workers(dossier)
        for worker in workers:
            if worker.get("task_id") == task_id:
                worker["phase"] = "archived"
                worker["last_used"] = _timestamp()
                payload = {"version": 1, "workers": workers}
                _atomic_json_write(_worker_path(dossier), payload)
                return worker
    raise DossierError(f"worker task_id not found: {task_id}")
