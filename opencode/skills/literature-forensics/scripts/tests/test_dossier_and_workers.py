from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from literature_forensics.dossier import (
    DossierError,
    archive_worker,
    initialize_dossier,
    list_workers,
    set_worker,
)


def test_init_creates_human_skeleton_and_never_overwrites(tmp_path):
    dossier = initialize_dossier(
        tmp_path / "dossier", "A careful title", "A bounded question"
    )

    assert "# A careful title" in (dossier / "README.md").read_text(encoding="utf-8")
    assert "```mermaid" in (dossier / "MAP.md").read_text(encoding="utf-8")
    assert (dossier / ".gitignore").read_text(
        encoding="utf-8"
    ) == ".state/\npapers/*.pdf\n"
    assert (dossier / "topics").is_dir()
    assert (dossier / "papers").is_dir()
    assert "## Current Bounded Answer" in (dossier / "README.md").read_text(
        encoding="utf-8"
    )
    assert "## Research Hunch" in (dossier / "brief.md").read_text(encoding="utf-8")
    assert "classDef gap" in (dossier / "MAP.md").read_text(encoding="utf-8")
    assert (dossier / "topics" / "README.md").is_file()
    assert (dossier / "papers" / "README.md").is_file()

    (dossier / "README.md").write_text("human edits\n", encoding="utf-8")
    with pytest.raises(DossierError):
        initialize_dossier(dossier, "Replacement")
    assert (dossier / "README.md").read_text(encoding="utf-8") == "human edits\n"


def test_worker_registry_is_atomic_and_archivable(tmp_path):
    dossier = initialize_dossier(tmp_path / "dossier", "Title")
    worker = set_worker(
        dossier,
        lane="metadata",
        task_id="task-1",
        phase="active",
        artifact="topics/metadata.md",
    )

    assert worker["artifact"] == "topics/metadata.md"
    registry = dossier / ".state" / "workers.json"
    assert (
        json.loads(registry.read_text(encoding="utf-8"))["workers"][0]["task_id"]
        == "task-1"
    )
    assert not list(registry.parent.glob("tmp*"))

    archived = archive_worker(dossier, task_id="task-1")
    assert archived["phase"] == "archived"
    assert list_workers(dossier)[0]["phase"] == "archived"


def test_force_only_repairs_unchanged_skeleton_and_never_resets_evidence(tmp_path):
    dossier = initialize_dossier(tmp_path / "dossier", "Title")
    (dossier / "MAP.md").unlink()
    initialize_dossier(dossier, "Title", force=True)
    assert (dossier / "MAP.md").is_file()

    (dossier / "README.md").write_text("human content\n", encoding="utf-8")
    with pytest.raises(DossierError, match="changed skeleton"):
        initialize_dossier(dossier, "Title", force=True)

    evidence = initialize_dossier(tmp_path / "evidence", "Evidence")
    (evidence / "papers" / "saved.pdf").write_bytes(b"%PDF-")
    with pytest.raises(DossierError, match="cached evidence or PDFs"):
        initialize_dossier(evidence, "Evidence", force=True)


def test_worker_lock_preserves_concurrent_updates(tmp_path):
    dossier = initialize_dossier(tmp_path / "dossier", "Title")

    def set_task(index: int) -> None:
        set_worker(dossier, lane="lane", task_id=f"task-{index}", phase="active")

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(set_task, range(8)))
    assert [worker["task_id"] for worker in list_workers(dossier)] == [
        f"task-{index}" for index in range(8)
    ]
