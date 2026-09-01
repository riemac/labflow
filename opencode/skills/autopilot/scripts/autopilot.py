#!/usr/bin/env python3
"""Manage deterministic, human-readable Autopilot run dossiers."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable
import uuid


SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_NOT_READY = 1
EXIT_USAGE = 2
EXIT_INTEGRITY = 3
EXIT_LOCAL = 4

MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_EXPLICIT_INPUT_BYTES = 2 * 1024 * 1024
MAX_OBJECTIVE_LENGTH = 4000
MAX_META_LENGTH = 2000
ZERO_DIGEST = "0" * 64
RUN_ID_PATTERN = re.compile(r"^\d{8}-\d{6}-[a-z0-9][a-z0-9-]{0,63}$")
ITEM_ID_PATTERN = re.compile(r"^[APR]\d{4}$")
TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
RUN_STATUSES = {
    "draft",
    "between-phases",
    "amendment-draft",
    "active",
    "reviewing",
    "review-rejected",
    "blocked",
    "review-approved",
    "finalized",
}
PROFILES = {"research", "coding", "paper"}
LEAF_EXAMPLES = {
    "run init": "labflow-autopilot run init --title 'Nightly method audit' --language zh-CN --stdin --json",
    "run status": "labflow-autopilot run status --run .autopilot/<run-id> --json",
    "run validate": "labflow-autopilot run validate --run .autopilot/<run-id> --json",
    "run finalize": "labflow-autopilot run finalize --run .autopilot/<run-id> --json",
    "run resume": "labflow-autopilot run resume --run .autopilot/<run-id> --reason 'User supplied the required decision'",
    "authority seal": "labflow-autopilot authority seal --run .autopilot/<run-id> --json",
    "authority verify": "labflow-autopilot authority verify --run .autopilot/<run-id> --json",
    "amendment new": "labflow-autopilot amendment new --run .autopilot/<run-id> --title 'Revised evaluation boundary'",
    "amendment seal": "labflow-autopilot amendment seal --run .autopilot/<run-id> --json",
    "amendment list": "labflow-autopilot amendment list --run .autopilot/<run-id> --json",
    "phase open": "labflow-autopilot phase open --run .autopilot/<run-id> --title 'Discriminate candidate mechanisms'",
    "phase close": "labflow-autopilot phase close --run .autopilot/<run-id> --json",
    "phase list": "labflow-autopilot phase list --run .autopilot/<run-id> --json",
    "review open": "labflow-autopilot review open --run .autopilot/<run-id> --json",
    "review probe": "labflow-autopilot review probe --run .autopilot/<run-id> --review-id R0001 --review-nonce <nonce> --task-id <session-id> --timeout-seconds 30 -- python3 verify.py",
    "review recover": "labflow-autopilot review recover --run .autopilot/<run-id> --review-id R0001 --review-nonce <nonce> --reason 'Reviewer host process terminated'",
    "review record": "labflow-autopilot review record --run .autopilot/<run-id> --stdin --json < review.json",
    "review list": "labflow-autopilot review list --run .autopilot/<run-id> --json",
    "goal render": "labflow-autopilot goal render --run .autopilot/<run-id> --json",
}
PLACEHOLDERS = {
    "待填写。",
    "待填写",
    "无。",
    "to be completed.",
    "to be completed",
    "none yet.",
    "none yet",
}

AUTHORITY_FILES = ("source.md", "contract.md", "envelope.md")
CONTRACT_FIELDS = (
    "intent",
    "success_boundary",
    "failure_boundary",
    "fixed_decisions",
    "non_goals",
    "method_freedom",
    "human_gates",
)
ENVELOPE_FIELDS = (
    "profile",
    "workspace",
    "write_scope",
    "git_policy",
    "budget",
    "max_turns",
    "max_duration_ms",
    "max_tokens",
    "resources",
    "side_effects",
    "stop_conditions",
)
PHASE_FIELDS = (
    "objective",
    "why_now",
    "entry_evidence",
    "exit_evidence",
    "allowed_pivots",
    "outcome",
    "next_rationale",
)
AMENDMENT_FIELDS = ("authorization", "change", "unchanged", "implications")
OUTCOME_FIELDS = (
    "contract_coverage",
    "decisive_evidence",
    "artifacts",
    "failed_routes",
    "limitations",
    "residual_risks",
    "handoff",
)


class CliError(RuntimeError):
    exit_code = EXIT_LOCAL


class NotReadyError(CliError):
    exit_code = EXIT_NOT_READY


class UsageError(CliError):
    exit_code = EXIT_USAGE


class IntegrityError(CliError):
    exit_code = EXIT_INTEGRITY


class LocalError(CliError):
    exit_code = EXIT_LOCAL


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _run_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:64]
    return slug or "run"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    _require_regular_file(path)
    return _sha256_bytes(path.read_bytes())


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _chain_digest(previous: str, item_digest: str) -> str:
    return _sha256_bytes(f"{previous}\n{item_digest}".encode("ascii"))


def _require_regular_file(path: Path) -> None:
    try:
        info = path.lstat()
    except FileNotFoundError as error:
        raise IntegrityError(f"required file is missing: {path}") from error
    if path.is_symlink() or not path.is_file():
        raise IntegrityError(f"expected a regular non-symlink file: {path}")
    if info.st_size > MAX_MANIFEST_BYTES and path.name == "manifest.json":
        raise IntegrityError(f"manifest exceeds {MAX_MANIFEST_BYTES} bytes: {path}")


def _run_file(run: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise IntegrityError("run-relative path is invalid")
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise IntegrityError(f"run-relative path escapes the dossier: {relative}")
    candidate = run / value
    if not candidate.resolve(strict=False).is_relative_to(run.resolve()):
        raise IntegrityError(f"run-relative path escapes the dossier: {relative}")
    return candidate


def _fsync_directory(path: Path) -> None:
    flags = getattr(os, "O_DIRECTORY", 0) | os.O_RDONLY
    try:
        handle = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


def _atomic_write(path: Path, text: str, *, replace: bool, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (path.is_symlink() or not path.is_file()):
        raise IntegrityError(f"refusing to replace a non-regular file: {path}")
    if path.exists() and not replace:
        raise NotReadyError(f"refusing to overwrite existing file: {path}")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        if path.exists() and not replace:
            raise NotReadyError(f"refusing to overwrite existing file: {path}")
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _write_json(path: Path, value: dict[str, Any], *, replace: bool = True) -> None:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    _atomic_write(path, text, replace=replace)


def _manifest_path(run: Path) -> Path:
    return run / "manifest.json"


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntegrityError(f"manifest {name} must be an object")
    return value


def _items(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise IntegrityError(f"manifest {name} must be an array")
    return value


def _counter(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise IntegrityError(f"manifest {name} must be a positive integer")
    return value


def _digest(value: Any, name: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise IntegrityError(f"manifest {name} must be a SHA-256 digest")
    return value


def _task_id(value: Any, name: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not TASK_ID_PATTERN.fullmatch(value):
        raise IntegrityError(f"manifest {name} has an invalid task ID")
    return value


def _record_path(run: Path, value: Any, name: str, pattern: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise IntegrityError(f"manifest {name} has an invalid dossier path")
    _run_file(run, value)
    return value


def _validate_manifest_shape(manifest: dict[str, Any], run: Path) -> None:
    status = manifest.get("status")
    if status not in RUN_STATUSES:
        raise IntegrityError(f"manifest has invalid status: {status!r}")
    if (
        not isinstance(manifest.get("language"), str)
        or not manifest["language"].strip()
    ):
        raise IntegrityError("manifest language must be non-empty")
    if (
        not isinstance(manifest.get("topicRoot"), str)
        or not Path(manifest["topicRoot"]).is_absolute()
    ):
        raise IntegrityError("manifest topicRoot must be an absolute path")
    if manifest.get("tracked") is not False:
        raise IntegrityError("Autopilot dossiers must remain local-only")

    authority = _mapping(manifest.get("authority"), "authority")
    sealed = authority.get("sealed")
    if not isinstance(sealed, bool):
        raise IntegrityError("manifest authority.sealed must be boolean")
    files = _mapping(authority.get("files"), "authority.files")
    if sealed:
        if set(files) != set(AUTHORITY_FILES):
            raise IntegrityError("sealed authority files are incomplete")
        for relative in AUTHORITY_FILES:
            _digest(files.get(relative), f"authority.files.{relative}")
        _digest(authority.get("baseHead"), "authority.baseHead")
        _digest(authority.get("head"), "authority.head")
    elif (
        files
        or authority.get("baseHead") is not None
        or authority.get("head") is not None
    ):
        raise IntegrityError("draft authority cannot carry sealed identities")
    amendments = _items(authority.get("amendments"), "authority.amendments")
    next_amendment = _counter(authority.get("nextAmendment"), "authority.nextAmendment")
    if next_amendment != len(amendments) + 1:
        raise IntegrityError("authority amendment counter is inconsistent")
    for index, amendment_value in enumerate(amendments, start=1):
        amendment = _mapping(amendment_value, f"authority.amendments[{index - 1}]")
        amendment_id = f"A{index:04d}"
        if amendment.get("id") != amendment_id:
            raise IntegrityError("amendment sequence is not contiguous")
        _record_path(
            run,
            amendment.get("path"),
            f"amendment {amendment_id}",
            rf"amendments/{amendment_id}-[a-z0-9-]+\.md",
        )
        _digest(amendment.get("sha256"), f"amendment {amendment_id}.sha256")
        _digest(amendment.get("head"), f"amendment {amendment_id}.head")
    draft_amendment = authority.get("draftAmendment")
    if draft_amendment is not None:
        draft = _mapping(draft_amendment, "authority.draftAmendment")
        amendment_id = f"A{next_amendment:04d}"
        if draft.get("id") != amendment_id:
            raise IntegrityError("draft amendment ID is inconsistent")
        _record_path(
            run,
            draft.get("path"),
            "draft amendment",
            rf"amendments/{amendment_id}-[a-z0-9-]+\.md",
        )

    phase = _mapping(manifest.get("phase"), "phase")
    closed = _items(phase.get("closed"), "phase.closed")
    next_phase = _counter(phase.get("next"), "phase.next")
    if next_phase != len(closed) + 1:
        raise IntegrityError("phase counter is inconsistent")
    for index, record_value in enumerate(closed, start=1):
        record = _mapping(record_value, f"phase.closed[{index - 1}]")
        phase_id = f"P{index:04d}"
        if record.get("id") != phase_id:
            raise IntegrityError("closed phase sequence is not contiguous")
        _record_path(
            run,
            record.get("path"),
            f"phase {phase_id}",
            rf"phases/{phase_id}-[a-z0-9-]+\.md",
        )
        _digest(record.get("sha256"), f"phase {phase_id}.sha256")
        _digest(record.get("authorityHead"), f"phase {phase_id}.authorityHead")
    current = phase.get("current")
    if current is not None:
        current_phase = _mapping(current, "phase.current")
        if current_phase.get("id") != f"P{next_phase:04d}":
            raise IntegrityError("current phase ID is inconsistent")
        _digest(current_phase.get("authorityHead"), "phase.current.authorityHead")

    review = _mapping(manifest.get("review"), "review")
    records = _items(review.get("records"), "review.records")
    next_review = _counter(review.get("next"), "review.next")
    if next_review != len(records) + 1:
        raise IntegrityError("review counter is inconsistent")
    reviewer_task = _task_id(review.get("taskId"), "review.taskId", optional=True)
    for index, record_value in enumerate(records, start=1):
        record = _mapping(record_value, f"review.records[{index - 1}]")
        review_id = f"R{index:04d}"
        if record.get("id") != review_id or record.get("verdict") not in {
            "approved",
            "rejected",
            "blocked",
        }:
            raise IntegrityError("review record identity or verdict is invalid")
        _record_path(
            run, record.get("path"), f"review {review_id}", rf"reviews/{review_id}\.md"
        )
        _digest(record.get("sha256"), f"review {review_id}.sha256")
        _digest(record.get("authorityHead"), f"review {review_id}.authorityHead")
        _digest(record.get("outcomeSha256"), f"review {review_id}.outcomeSha256")
        if not isinstance(record.get("reviewNonce"), str) or not re.fullmatch(
            r"[0-9a-f]{32}", record["reviewNonce"]
        ):
            raise IntegrityError(f"review {review_id} nonce is invalid")
        if (
            reviewer_task
            and _task_id(record.get("taskId"), f"review {review_id}.taskId")
            != reviewer_task
        ):
            raise IntegrityError("review records do not share one task identity")
        closed_count = record.get("closedPhaseCount")
        if (
            not isinstance(closed_count, int)
            or isinstance(closed_count, bool)
            or not 1 <= closed_count <= len(closed)
        ):
            raise IntegrityError(f"review {review_id} closedPhaseCount is invalid")
    opened = review.get("open")
    if opened is not None:
        open_review = _mapping(opened, "review.open")
        review_id = f"R{next_review:04d}"
        if open_review.get("id") != review_id:
            raise IntegrityError("open review ID is inconsistent")
        _digest(open_review.get("authorityHead"), "review.open.authorityHead")
        _digest(open_review.get("outcomeSha256"), "review.open.outcomeSha256")
        nonce = open_review.get("nonce")
        if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{32}", nonce):
            raise IntegrityError("open review nonce is invalid")
        _record_path(
            run,
            open_review.get("probeRoot"),
            "review probe root",
            rf"reviews/probes/{review_id}",
        )
        used = open_review.get("probeUsedSeconds")
        probes = _items(open_review.get("probes"), "review.open.probes")
        in_flight = _items(
            open_review.get("probeInFlight"), "review.open.probeInFlight"
        )
        probe_next = _counter(open_review.get("probeNext"), "review.open.probeNext")
        if not isinstance(used, int) or isinstance(used, bool) or not 0 <= used <= 600:
            raise IntegrityError("review probe budget is invalid")
        closed_count = open_review.get("closedPhaseCount")
        if (
            not isinstance(closed_count, int)
            or isinstance(closed_count, bool)
            or not 1 <= closed_count <= len(closed)
        ):
            raise IntegrityError("open review closedPhaseCount is invalid")
        seen_probe_ids: set[str] = set()
        for probe_index, probe_value in enumerate(probes, start=1):
            probe = _mapping(probe_value, f"review.open.probes[{probe_index - 1}]")
            probe_id = probe.get("id")
            if not isinstance(probe_id, str) or not re.fullmatch(
                r"probe-\d{4}", probe_id
            ):
                raise IntegrityError("review probe identity is invalid")
            if probe_id in seen_probe_ids:
                raise IntegrityError("review probe identities are duplicated")
            seen_probe_ids.add(probe_id)
            relative = _record_path(
                run,
                probe.get("path"),
                "review probe",
                rf"reviews/probes/{review_id}/{probe_id}\.json",
            )
            _digest(probe.get("sha256"), f"review probe {relative}.sha256")
        seen_in_flight: set[str] = set()
        for reservation_value in in_flight:
            reservation = _mapping(reservation_value, "review probe reservation")
            probe_id = reservation.get("id")
            if not isinstance(probe_id, str) or not re.fullmatch(
                r"probe-\d{4}", probe_id
            ):
                raise IntegrityError("review in-flight probe identity is invalid")
            if probe_id in seen_probe_ids or probe_id in seen_in_flight:
                raise IntegrityError("review probe identities are duplicated")
            owner_pid = reservation.get("ownerPid")
            deadline = reservation.get("deadlineEpoch")
            if (
                not isinstance(owner_pid, int)
                or isinstance(owner_pid, bool)
                or owner_pid < 1
            ):
                raise IntegrityError("review probe reservation owner PID is invalid")
            if (
                not isinstance(deadline, (int, float))
                or isinstance(deadline, bool)
                or deadline <= 0
            ):
                raise IntegrityError("review probe reservation deadline is invalid")
            if (
                not isinstance(reservation.get("ownerStart"), str)
                or not reservation["ownerStart"]
            ):
                raise IntegrityError(
                    "review probe reservation process identity is invalid"
                )
            seen_in_flight.add(probe_id)
        allocated = [
            int(item.split("-")[1]) for item in [*seen_probe_ids, *seen_in_flight]
        ]
        if allocated and probe_next <= max(allocated):
            raise IntegrityError("review probe counter is inconsistent")
        open_task = _task_id(
            open_review.get("taskId"), "review.open.taskId", optional=True
        )
        if open_task and reviewer_task and open_task != reviewer_task:
            raise IntegrityError("open review task identity is inconsistent")

    outcome = _mapping(manifest.get("outcome"), "outcome")
    _digest(outcome.get("sha256"), "outcome.sha256", optional=True)
    if status == "finalized" and not isinstance(outcome.get("finalizedAt"), str):
        raise IntegrityError("finalized run lacks outcome.finalizedAt")

    if status == "draft" and sealed:
        raise IntegrityError("draft run cannot have sealed authority")
    if not sealed and status != "draft":
        raise IntegrityError("unsealed authority requires draft status")
    if status == "amendment-draft" and draft_amendment is None:
        raise IntegrityError("amendment-draft status lacks a draft amendment")
    if draft_amendment is not None and status != "amendment-draft":
        raise IntegrityError("draft amendment requires amendment-draft status")
    if status == "active" and current is None:
        raise IntegrityError("active status lacks a current phase")
    if current is not None and status != "active":
        raise IntegrityError("current phase requires active status")
    if status == "reviewing" and opened is None:
        raise IntegrityError("reviewing status lacks an open review")
    if opened is not None and status != "reviewing":
        raise IntegrityError("open review requires reviewing status")
    if status == "review-approved" and (
        not records or records[-1].get("verdict") != "approved"
    ):
        raise IntegrityError("review-approved status lacks an approved latest review")
    if status == "review-rejected" and (
        not records or records[-1].get("verdict") != "rejected"
    ):
        raise IntegrityError("review-rejected status lacks a rejected latest review")
    if status == "blocked" and (not records or records[-1].get("verdict") != "blocked"):
        raise IntegrityError("blocked status lacks a blocked latest review")
    if status == "finalized":
        if (
            not closed
            or current is not None
            or opened is not None
            or draft_amendment is not None
        ):
            raise IntegrityError("finalized run has incomplete lifecycle state")
        if not records or records[-1].get("verdict") != "approved":
            raise IntegrityError("finalized run lacks a latest approved review")
        if records[-1].get("authorityHead") != authority.get("head"):
            raise IntegrityError("finalized review targets an obsolete authority head")
        if records[-1].get("outcomeSha256") != outcome.get("sha256"):
            raise IntegrityError("finalized review and outcome identities differ")
    for index, event in enumerate(_items(manifest.get("resumptions"), "resumptions")):
        value = _mapping(event, f"resumptions[{index}]")
        if not isinstance(value.get("reason"), str) or not value["reason"].strip():
            raise IntegrityError("resumption reason must be non-empty")


def _load_manifest(run: Path) -> dict[str, Any]:
    path = _manifest_path(run)
    _require_regular_file(path)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise IntegrityError(f"could not parse manifest: {error}") from error
    if (
        not isinstance(manifest, dict)
        or manifest.get("schemaVersion") != SCHEMA_VERSION
    ):
        raise IntegrityError(f"manifest must declare schemaVersion {SCHEMA_VERSION}")
    if manifest.get("runId") != run.name or not RUN_ID_PATTERN.fullmatch(run.name):
        raise IntegrityError("manifest runId does not match its run directory")
    _validate_manifest_shape(manifest, run)
    return manifest


def _save_manifest(run: Path, manifest: dict[str, Any]) -> None:
    manifest["updatedAt"] = _utc_now()
    _write_json(_manifest_path(run), manifest)


def _discover_run(value: str | None) -> Path:
    if value:
        run = Path(value).expanduser().resolve()
    else:
        current = Path.cwd().resolve()
        run = None
        for candidate in (current, *current.parents):
            if (candidate / "manifest.json").is_file():
                run = candidate
                break
        if run is None:
            raise UsageError("no run found from the current directory; pass --run")
    if not run.is_dir():
        raise UsageError(f"run directory does not exist: {run}")
    _load_manifest(run)
    return run


def _git_root() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path.cwd(),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise UsageError("no Git root found; pass --root explicitly") from error
    root = Path(result.stdout.strip()).resolve()
    if not root.is_dir():
        raise UsageError("git rev-parse did not return a directory")
    return root


def _topic_root(value: str | None) -> Path:
    root = Path(value).expanduser().resolve() if value else _git_root()
    if not root.is_dir():
        raise UsageError(f"topic root does not exist: {root}")
    return root


def _marker(document: str, field: str, edge: str) -> str:
    return f"<!-- autopilot:{document}:{field}:{edge} -->"


def _field(document: str, field: str, value: str) -> str:
    return f"{_marker(document, field, 'start')}\n{value}\n{_marker(document, field, 'end')}"


def _extract(text: str, document: str, field: str) -> str:
    start = re.escape(_marker(document, field, "start"))
    end = re.escape(_marker(document, field, "end"))
    matches = re.findall(rf"{start}\s*([\s\S]*?)\s*{end}", text)
    if len(matches) != 1:
        raise NotReadyError(
            f"{document}.{field} must have exactly one stable marker pair"
        )
    return matches[0].strip()


def _meaningful(value: str) -> bool:
    normalized = value.strip().lower()
    return bool(normalized) and normalized not in PLACEHOLDERS


def _read_document(run: Path, relative: str) -> str:
    path = _run_file(run, relative)
    _require_regular_file(path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise LocalError(f"could not read {path}: {error}") from error


def _require_fields(
    run: Path, relative: str, document: str, fields: Iterable[str]
) -> dict[str, str]:
    text = _read_document(run, relative)
    values = {field: _extract(text, document, field) for field in fields}
    missing = [field for field, value in values.items() if not _meaningful(value)]
    if missing:
        raise NotReadyError(f"{relative} has incomplete sections: {', '.join(missing)}")
    return values


def _labels(language: str) -> dict[str, str]:
    if language.lower().startswith("zh"):
        return {
            "pending": "待填写。",
            "source_title": "Autopilot 原始合意材料",
            "approved_plan": "批准的计划",
            "decisions": "后续拍板原文",
            "contract_title": "Autopilot 高层语义合同",
            "intent": "总体意图",
            "success_boundary": "成功边界",
            "failure_boundary": "失败与可行性边界",
            "fixed_decisions": "固定决策",
            "non_goals": "非目标",
            "method_freedom": "方法自由度",
            "human_gates": "必须由人判断的验收门",
            "envelope_title": "Autopilot 执行授权",
            "profile": "主 Profile",
            "workspace": "工作区与产物根",
            "write_scope": "读写边界",
            "git_policy": "Git 策略",
            "budget": "时间与调用预算",
            "max_turns": "Goal 最大续行次数",
            "max_duration_ms": "Goal 最大持续毫秒数",
            "max_tokens": "Goal 最大上下文 Token",
            "resources": "资源约束",
            "side_effects": "外部副作用授权",
            "stop_conditions": "停止与阻塞条件",
            "phase_title": "Semantic Phase",
            "objective": "当前语义目标",
            "why_now": "为什么现在做",
            "entry_evidence": "进入依据",
            "exit_evidence": "退出证据",
            "allowed_pivots": "允许的探索与转向",
            "outcome": "阶段结论与证据",
            "next_rationale": "下一阶段理由",
            "amendment_title": "合同修订",
            "authorization": "用户授权原文",
            "change": "有效语义变化",
            "unchanged": "保持不变的边界",
            "implications": "对当前运行的影响",
            "outcome_title": "Autopilot 最终结果",
            "contract_coverage": "合同逐项覆盖",
            "decisive_evidence": "决定性证据",
            "artifacts": "保留产物",
            "failed_routes": "失败与放弃路线",
            "limitations": "已知限制",
            "residual_risks": "残余风险",
            "handoff": "复现与交接",
        }
    return {
        "pending": "To be completed.",
        "source_title": "Autopilot Source Agreement",
        "approved_plan": "Approved Plan",
        "decisions": "Subsequent Decisive User Instructions",
        "contract_title": "Autopilot Semantic Contract",
        "intent": "Overall Intent",
        "success_boundary": "Success Boundary",
        "failure_boundary": "Failure And Feasibility Boundary",
        "fixed_decisions": "Fixed Decisions",
        "non_goals": "Non-Goals",
        "method_freedom": "Method Freedom",
        "human_gates": "Human Judgment Gates",
        "envelope_title": "Autopilot Execution Envelope",
        "profile": "Primary Profile",
        "workspace": "Workspace And Artifact Root",
        "write_scope": "Read And Write Boundary",
        "git_policy": "Git Strategy",
        "budget": "Time And Call Budget",
        "max_turns": "Goal Maximum Auto-Continues",
        "max_duration_ms": "Goal Maximum Duration Milliseconds",
        "max_tokens": "Goal Maximum Context Tokens",
        "resources": "Resource Constraints",
        "side_effects": "External Side-Effect Authorization",
        "stop_conditions": "Stop And Block Conditions",
        "phase_title": "Semantic Phase",
        "objective": "Current Semantic Objective",
        "why_now": "Why This Phase Now",
        "entry_evidence": "Entry Evidence",
        "exit_evidence": "Exit Evidence",
        "allowed_pivots": "Allowed Exploration And Pivots",
        "outcome": "Phase Outcome And Evidence",
        "next_rationale": "Rationale For The Next Phase",
        "amendment_title": "Contract Amendment",
        "authorization": "Authorizing User Instruction",
        "change": "Effective Semantic Change",
        "unchanged": "Unchanged Boundaries",
        "implications": "Run Implications",
        "outcome_title": "Autopilot Outcome",
        "contract_coverage": "Contract Coverage",
        "decisive_evidence": "Decisive Evidence",
        "artifacts": "Retained Artifacts",
        "failed_routes": "Failed And Abandoned Routes",
        "limitations": "Known Limitations",
        "residual_risks": "Residual Risks",
        "handoff": "Reproduction And Handoff",
    }


def _document(title: str, document: str, sections: list[tuple[str, str, str]]) -> str:
    blocks = [f"# {title}"]
    for field, heading, value in sections:
        blocks.extend([f"## {heading}", _field(document, field, value)])
    return "\n\n".join(blocks) + "\n"


def _source_template(language: str, approved_plan: str = "") -> str:
    labels = _labels(language)
    return _document(
        labels["source_title"],
        "source",
        [
            (
                "approved_plan",
                labels["approved_plan"],
                approved_plan.strip() or labels["pending"],
            ),
            ("decisions", labels["decisions"], labels["pending"]),
        ],
    )


def _contract_template(language: str) -> str:
    labels = _labels(language)
    return _document(
        labels["contract_title"],
        "contract",
        [(field, labels[field], labels["pending"]) for field in CONTRACT_FIELDS],
    )


def _envelope_template(language: str) -> str:
    labels = _labels(language)
    return _document(
        labels["envelope_title"],
        "envelope",
        [(field, labels[field], labels["pending"]) for field in ENVELOPE_FIELDS],
    )


def _phase_template(
    language: str, phase_id: str, title: str, authority_head: str
) -> str:
    labels = _labels(language)
    prefix = [
        f"# {labels['phase_title']} {phase_id}: {title}",
        f"<!-- autopilot:phase:id={phase_id} authority={authority_head} -->",
    ]
    body = _document(
        "",
        "phase",
        [(field, labels[field], labels["pending"]) for field in PHASE_FIELDS],
    ).removeprefix("# \n\n")
    return "\n\n".join(prefix) + "\n\n" + body


def _amendment_template(
    language: str, amendment_id: str, title: str, prior_head: str
) -> str:
    labels = _labels(language)
    prefix = [
        f"# {labels['amendment_title']} {amendment_id}: {title}",
        f"<!-- autopilot:amendment:id={amendment_id} prior={prior_head} -->",
    ]
    body = _document(
        "",
        "amendment",
        [(field, labels[field], labels["pending"]) for field in AMENDMENT_FIELDS],
    ).removeprefix("# \n\n")
    return "\n\n".join(prefix) + "\n\n" + body


def _outcome_template(language: str) -> str:
    labels = _labels(language)
    return _document(
        labels["outcome_title"],
        "outcome",
        [(field, labels[field], labels["pending"]) for field in OUTCOME_FIELDS],
    )


def _initial_manifest(run_id: str, topic_root: Path, language: str) -> dict[str, Any]:
    now = _utc_now()
    return {
        "schemaVersion": SCHEMA_VERSION,
        "runId": run_id,
        "status": "draft",
        "language": language,
        "topicRoot": str(topic_root),
        "tracked": False,
        "createdAt": now,
        "updatedAt": now,
        "authority": {
            "sealed": False,
            "sealedAt": None,
            "files": {},
            "baseHead": None,
            "head": None,
            "nextAmendment": 1,
            "draftAmendment": None,
            "amendments": [],
        },
        "phase": {"next": 1, "current": None, "closed": []},
        "review": {"next": 1, "taskId": None, "open": None, "records": []},
        "outcome": {"sha256": None, "finalizedAt": None},
        "resumptions": [],
    }


def _verify_authority(run: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    authority = manifest.get("authority")
    if not isinstance(authority, dict) or authority.get("sealed") is not True:
        raise NotReadyError("authority is not sealed")
    files = authority.get("files")
    if not isinstance(files, dict) or set(files) != set(AUTHORITY_FILES):
        raise IntegrityError("authority file identities are incomplete")
    for relative in AUTHORITY_FILES:
        if _sha256(_run_file(run, relative)) != files.get(relative):
            raise IntegrityError(f"sealed authority hash mismatch: {relative}")
    base_head = _canonical_digest(files)
    if authority.get("baseHead") != base_head:
        raise IntegrityError("authority base head mismatch")
    head = base_head
    amendments = authority.get("amendments")
    if not isinstance(amendments, list):
        raise IntegrityError("authority amendments must be a list")
    for index, amendment in enumerate(amendments, start=1):
        if not isinstance(amendment, dict) or amendment.get("id") != f"A{index:04d}":
            raise IntegrityError("amendment sequence is not contiguous")
        relative = amendment.get("path")
        digest = amendment.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise IntegrityError("amendment identity is malformed")
        if _sha256(_run_file(run, relative)) != digest:
            raise IntegrityError(f"sealed amendment hash mismatch: {relative}")
        head = _chain_digest(head, digest)
        if amendment.get("head") != head:
            raise IntegrityError(f"amendment chain mismatch: {relative}")
    if authority.get("head") != head:
        raise IntegrityError("authority head mismatch")
    return authority


def _validate_closed_phases(run: Path, manifest: dict[str, Any]) -> None:
    phase = manifest.get("phase")
    if not isinstance(phase, dict) or not isinstance(phase.get("closed"), list):
        raise IntegrityError("phase state is malformed")
    for index, record in enumerate(phase["closed"], start=1):
        if not isinstance(record, dict) or record.get("id") != f"P{index:04d}":
            raise IntegrityError("closed phase sequence is not contiguous")
        relative = record.get("path")
        if not isinstance(relative, str) or _sha256(
            _run_file(run, relative)
        ) != record.get("sha256"):
            raise IntegrityError(f"closed phase hash mismatch: {relative}")
    current = phase.get("current")
    current_path = run / "phases" / "current.md"
    if current is None:
        if current_path.exists():
            raise IntegrityError("phases/current.md exists without a manifest owner")
    else:
        if not isinstance(current, dict) or not ITEM_ID_PATTERN.fullmatch(
            str(current.get("id", ""))
        ):
            raise IntegrityError("current phase identity is malformed")
        _require_regular_file(current_path)


def _validate_reviews(run: Path, manifest: dict[str, Any]) -> None:
    review = manifest.get("review")
    if not isinstance(review, dict) or not isinstance(review.get("records"), list):
        raise IntegrityError("review state is malformed")
    task_id = review.get("taskId")
    for index, record in enumerate(review["records"], start=1):
        if not isinstance(record, dict) or record.get("id") != f"R{index:04d}":
            raise IntegrityError("review sequence is not contiguous")
        relative = record.get("path")
        if not isinstance(relative, str) or _sha256(
            _run_file(run, relative)
        ) != record.get("sha256"):
            raise IntegrityError(f"review hash mismatch: {relative}")
        if task_id and record.get("taskId") != task_id:
            raise IntegrityError(
                "review records do not share one reviewer task identity"
            )
        stored = _stored_review_claim(_run_file(run, relative))
        expected = {
            "reviewId": record["id"],
            "reviewerTaskId": record["taskId"],
            "reviewNonce": record["reviewNonce"],
            "authorityHead": record["authorityHead"],
            "outcomeSha256": record["outcomeSha256"],
            "verdict": record["verdict"],
        }
        mismatched = [
            field for field, value in expected.items() if stored.get(field) != value
        ]
        if mismatched:
            raise IntegrityError(
                f"review {record['id']} metadata disagrees with its structured verdict: "
                + ", ".join(mismatched)
            )
    opened = review.get("open")
    if opened is not None:
        if not isinstance(opened, dict):
            raise IntegrityError("open review state is malformed")
        probe_root = opened.get("probeRoot")
        if not isinstance(probe_root, str) or not _run_file(run, probe_root).is_dir():
            raise IntegrityError("open review probe root is missing")
        for probe in opened.get("probes", []):
            relative = probe.get("path")
            if not isinstance(relative, str) or _sha256(
                _run_file(run, relative)
            ) != probe.get("sha256"):
                raise IntegrityError(f"review probe hash mismatch: {relative}")


def _validate_run(run: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    for path in run.rglob("*"):
        if path.is_symlink():
            raise IntegrityError(
                f"run dossier contains a symlink: {path.relative_to(run)}"
            )
        if path.name.startswith(".") and ".tmp-" in path.name:
            raise IntegrityError(
                f"run dossier contains a temporary file: {path.relative_to(run)}"
            )
    ignore_path = _run_file(run, ".gitignore")
    _require_regular_file(ignore_path)
    if ignore_path.read_text(encoding="utf-8") != "*\n":
        raise IntegrityError("run-local .gitignore must remain exactly '*\\n'")
    _require_regular_file(_run_file(run, "reviews/.probe.lock"))
    authority = manifest.get("authority", {})
    if authority.get("sealed") is True:
        _verify_authority(run, manifest)
    else:
        for relative in (*AUTHORITY_FILES, "outcome.md"):
            _require_regular_file(run / relative)
    _validate_closed_phases(run, manifest)
    _validate_reviews(run, manifest)
    outcome = manifest.get("outcome")
    if not isinstance(outcome, dict):
        raise IntegrityError("outcome state is malformed")
    if manifest.get("status") == "finalized":
        digest = _sha256(_run_file(run, "outcome.md"))
        if outcome.get("sha256") != digest or not outcome.get("finalizedAt"):
            raise IntegrityError("finalized outcome identity is invalid")
    return {
        "runId": manifest["runId"],
        "status": manifest.get("status"),
        "authorityHead": authority.get("head"),
        "currentPhase": manifest.get("phase", {}).get("current", {}).get("id")
        if manifest.get("phase", {}).get("current")
        else None,
        "reviewerTaskId": manifest.get("review", {}).get("taskId"),
    }


def _result(operation: str, message: str, **data: Any) -> dict[str, Any]:
    return {
        "version": 1,
        "operation": operation,
        "ok": True,
        "message": message,
        **data,
    }


def _emit(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        )
        return
    print(payload.get("message", ""))
    data = payload.get("data")
    if isinstance(data, dict):
        for key, value in data.items():
            if value is not None:
                print(f"{key}: {value}")


def command_run_init(args: argparse.Namespace) -> dict[str, Any]:
    root = _topic_root(args.root)
    run_id = f"{_run_timestamp()}-{_slug(args.slug or args.title)}"
    run = root / ".autopilot" / run_id
    if run.exists():
        raise NotReadyError(f"run already exists: {run}")
    approved_plan = sys.stdin.read(MAX_EXPLICIT_INPUT_BYTES + 1) if args.stdin else ""
    if len(approved_plan.encode("utf-8")) > MAX_EXPLICIT_INPUT_BYTES:
        raise UsageError(f"approved plan exceeds {MAX_EXPLICIT_INPUT_BYTES} bytes")
    owned = False
    try:
        run.mkdir(parents=True, exist_ok=False)
        owned = True
        for relative in ("amendments", "phases", "reviews", "reviews/probes"):
            (run / relative).mkdir(parents=True, exist_ok=False)
        os.chmod(run, 0o700)
        _atomic_write(run / ".gitignore", "*\n", replace=False, mode=0o600)
        _atomic_write(run / "reviews" / ".probe.lock", "", replace=False, mode=0o600)
        _atomic_write(
            run / "source.md",
            _source_template(args.language, approved_plan),
            replace=False,
        )
        _atomic_write(
            run / "contract.md", _contract_template(args.language), replace=False
        )
        _atomic_write(
            run / "envelope.md", _envelope_template(args.language), replace=False
        )
        _atomic_write(
            run / "outcome.md", _outcome_template(args.language), replace=False
        )
        manifest = _initial_manifest(run_id, root, args.language)
        _write_json(_manifest_path(run), manifest, replace=False)
    except Exception:
        # A failed init owns the new run directory and may remove only that path.
        if owned and run.exists():
            shutil.rmtree(run, ignore_errors=True)
        raise
    return _result(
        "run.init",
        "Autopilot run initialized.",
        data={"run": str(run), "runId": run_id},
    )


def command_run_status(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    data = _validate_run(run, manifest)
    data["run"] = str(run)
    data["amendments"] = len(manifest["authority"]["amendments"])
    data["closedPhases"] = len(manifest["phase"]["closed"])
    data["reviews"] = len(manifest["review"]["records"])
    return _result(
        "run.status",
        f"Autopilot run {manifest['runId']}: {manifest['status']}",
        data=data,
    )


def command_run_validate(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    data = _validate_run(run, manifest)
    if manifest["authority"].get("sealed") is not True:
        raise NotReadyError("run structure is valid, but authority is not sealed")
    return _result("run.validate", "Autopilot run is structurally valid.", data=data)


def command_run_resume(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    _require_quiet_boundary(manifest, "resume the run", {"blocked"})
    reason = args.reason.strip()
    if not reason:
        raise UsageError("resume reason must be non-empty")
    manifest["resumptions"].append({"reason": reason, "at": _utc_now()})
    manifest["status"] = "between-phases"
    _save_manifest(run, manifest)
    return _result("run.resume", "Blocked Autopilot run resumed explicitly.")


def command_authority_seal(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    authority = manifest["authority"]
    if authority.get("sealed") is True:
        _verify_authority(run, manifest)
        return _result(
            "authority.seal",
            "Authority is already sealed.",
            data={"head": authority["head"]},
        )
    _require_status(manifest, "seal authority", {"draft"})
    source = _read_document(run, "source.md")
    source_values = {
        field: _extract(source, "source", field)
        for field in ("approved_plan", "decisions")
    }
    if not any(_meaningful(value) for value in source_values.values()):
        raise NotReadyError(
            "source.md needs an approved plan or decisive user instruction"
        )
    _require_fields(run, "contract.md", "contract", CONTRACT_FIELDS)
    envelope = _require_fields(run, "envelope.md", "envelope", ENVELOPE_FIELDS)
    if envelope["profile"].strip().lower() not in PROFILES:
        raise NotReadyError("envelope profile must be research, coding, or paper")
    for field in ("max_turns", "max_duration_ms", "max_tokens"):
        if not re.fullmatch(r"[1-9]\d*", envelope[field].strip()):
            raise NotReadyError(f"envelope {field} must be a positive integer")
    files = {
        relative: _sha256(_run_file(run, relative)) for relative in AUTHORITY_FILES
    }
    base_head = _canonical_digest(files)
    authority.update(
        {
            "sealed": True,
            "sealedAt": _utc_now(),
            "files": files,
            "baseHead": base_head,
            "head": base_head,
        }
    )
    manifest["status"] = "between-phases"
    _save_manifest(run, manifest)
    return _result(
        "authority.seal", "Authority sealed.", data={"head": base_head, "files": files}
    )


def command_authority_verify(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    authority = _verify_authority(run, _load_manifest(run))
    return _result(
        "authority.verify",
        "Authority integrity verified.",
        data={"head": authority["head"]},
    )


def _require_status(
    manifest: dict[str, Any], operation: str, allowed: set[str]
) -> None:
    if manifest.get("status") not in allowed:
        expected = ", ".join(sorted(allowed))
        raise NotReadyError(
            f"cannot {operation} from status {manifest.get('status')!r}; expected {expected}"
        )


def _require_quiet_boundary(
    manifest: dict[str, Any], operation: str, allowed: set[str]
) -> None:
    _require_status(manifest, operation, allowed)
    if manifest["phase"].get("current") is not None:
        raise NotReadyError(f"cannot {operation}: close the current phase first")
    if manifest["review"].get("open") is not None:
        raise NotReadyError(f"cannot {operation}: record the open review first")


def command_amendment_new(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    authority = _verify_authority(run, manifest)
    _require_quiet_boundary(
        manifest,
        "open an amendment",
        {"between-phases", "review-rejected"},
    )
    if authority.get("draftAmendment") is not None:
        raise NotReadyError("an amendment draft is already open")
    index = authority["nextAmendment"]
    amendment_id = f"A{index:04d}"
    relative = f"amendments/{amendment_id}-{_slug(args.slug or args.title)}.md"
    destination = _run_file(run, relative)
    created = False
    try:
        _atomic_write(
            destination,
            _amendment_template(
                manifest["language"], amendment_id, args.title, authority["head"]
            ),
            replace=False,
        )
        created = True
        authority["draftAmendment"] = {
            "id": amendment_id,
            "path": relative,
            "title": args.title,
        }
        manifest["status"] = "amendment-draft"
        _save_manifest(run, manifest)
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return _result(
        "amendment.new",
        f"Created amendment draft {amendment_id}.",
        data={"path": str(run / relative), "id": amendment_id},
    )


def command_amendment_seal(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    authority = _verify_authority(run, manifest)
    _require_quiet_boundary(manifest, "seal an amendment", {"amendment-draft"})
    draft = authority.get("draftAmendment")
    if not isinstance(draft, dict):
        raise NotReadyError("no amendment draft is open")
    amendment_text = _read_document(run, draft["path"])
    expected_identity = (
        f"<!-- autopilot:amendment:id={draft['id']} prior={authority['head']} -->"
    )
    if expected_identity not in amendment_text:
        raise IntegrityError(
            "amendment identity does not match the current authority head"
        )
    _require_fields(run, draft["path"], "amendment", AMENDMENT_FIELDS)
    digest = _sha256(_run_file(run, draft["path"]))
    head = _chain_digest(authority["head"], digest)
    authority["amendments"].append(
        {
            **draft,
            "sha256": digest,
            "head": head,
            "sealedAt": _utc_now(),
        }
    )
    authority["head"] = head
    authority["nextAmendment"] += 1
    authority["draftAmendment"] = None
    manifest["status"] = "between-phases"
    _save_manifest(run, manifest)
    return _result(
        "amendment.seal",
        f"Sealed amendment {draft['id']}.",
        data={"head": head, "sha256": digest},
    )


def command_amendment_list(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    authority = _verify_authority(run, manifest)
    return _result(
        "amendment.list",
        f"{len(authority['amendments'])} sealed amendment(s).",
        data={"head": authority["head"], "items": authority["amendments"]},
    )


def command_phase_open(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    authority = _verify_authority(run, manifest)
    _require_status(manifest, "open a phase", {"between-phases", "review-rejected"})
    if manifest["phase"].get("current") is not None:
        raise NotReadyError("a semantic phase is already open")
    if manifest["authority"].get("draftAmendment") is not None:
        raise NotReadyError("seal the amendment draft before opening a phase")
    if manifest["review"].get("open") is not None:
        raise NotReadyError("record the open review before opening a phase")
    index = manifest["phase"]["next"]
    phase_id = f"P{index:04d}"
    relative = "phases/current.md"
    destination = _run_file(run, relative)
    created = False
    try:
        _atomic_write(
            destination,
            _phase_template(
                manifest["language"], phase_id, args.title, authority["head"]
            ),
            replace=False,
        )
        created = True
        manifest["phase"]["current"] = {
            "id": phase_id,
            "title": args.title,
            "authorityHead": authority["head"],
            "openedAt": _utc_now(),
        }
        manifest["status"] = "active"
        _save_manifest(run, manifest)
    except Exception:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return _result(
        "phase.open",
        f"Opened semantic phase {phase_id}.",
        data={"path": str(run / relative), "id": phase_id},
    )


def command_phase_close(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    authority = _verify_authority(run, manifest)
    _require_status(manifest, "close a phase", {"active"})
    current = manifest["phase"].get("current")
    if not isinstance(current, dict):
        raise NotReadyError("no semantic phase is open")
    if current.get("authorityHead") != authority["head"]:
        raise IntegrityError(
            "current phase was opened against a different authority head"
        )
    phase_text = _read_document(run, "phases/current.md")
    expected_identity = (
        f"<!-- autopilot:phase:id={current['id']} authority={authority['head']} -->"
    )
    if expected_identity not in phase_text:
        raise IntegrityError(
            "current phase identity does not match the effective authority"
        )
    _require_fields(run, "phases/current.md", "phase", PHASE_FIELDS)
    relative = f"phases/{current['id']}-{_slug(args.slug or current['title'])}.md"
    destination = run / relative
    if destination.exists():
        raise NotReadyError(f"phase destination already exists: {destination}")
    source = run / "phases/current.md"
    try:
        os.replace(source, destination)
        digest = _sha256(destination)
        record = {**current, "path": relative, "sha256": digest, "closedAt": _utc_now()}
        manifest["phase"]["closed"].append(record)
        manifest["phase"]["next"] += 1
        manifest["phase"]["current"] = None
        manifest["status"] = "between-phases"
        _save_manifest(run, manifest)
    except Exception:
        if destination.exists() and not source.exists():
            os.replace(destination, source)
        raise
    return _result(
        "phase.close",
        f"Closed semantic phase {current['id']}.",
        data={"path": str(destination), "sha256": digest},
    )


def command_phase_list(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    _validate_closed_phases(run, manifest)
    return _result(
        "phase.list",
        f"{len(manifest['phase']['closed'])} closed phase(s).",
        data={
            "current": manifest["phase"]["current"],
            "closed": manifest["phase"]["closed"],
        },
    )


def _validate_outcome(run: Path) -> dict[str, str]:
    return _require_fields(run, "outcome.md", "outcome", OUTCOME_FIELDS)


def command_review_open(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    authority = _verify_authority(run, manifest)
    _require_quiet_boundary(manifest, "open a review", {"between-phases"})
    if not manifest["phase"]["closed"]:
        raise NotReadyError("close at least one semantic phase before review")
    _validate_outcome(run)
    review = manifest["review"]
    review_id = f"R{review['next']:04d}"
    probe_relative = f"reviews/probes/{review_id}"
    probe_root = _run_file(run, probe_relative)
    outcome_digest = _sha256(_run_file(run, "outcome.md"))
    previous = review["records"][-1] if review["records"] else None
    open_review = {
        "id": review_id,
        "authorityHead": authority["head"],
        "outcomeSha256": outcome_digest,
        "probeRoot": probe_relative,
        "nonce": secrets.token_hex(16),
        "taskId": review.get("taskId"),
        "probeUsedSeconds": 0,
        "probeNext": 1,
        "probeInFlight": [],
        "probes": [],
        "closedPhaseCount": len(manifest["phase"]["closed"]),
        "openedAt": _utc_now(),
    }
    created = False
    try:
        probe_root.mkdir(parents=True, exist_ok=False)
        created = True
        review["open"] = open_review
        manifest["status"] = "reviewing"
        _save_manifest(run, manifest)
    except Exception:
        if created and probe_root.is_dir():
            probe_root.rmdir()
        raise
    previous_phase_count = previous.get("closedPhaseCount", 0) if previous else 0
    remediation_phases = [
        item["id"] for item in manifest["phase"]["closed"][previous_phase_count:]
    ]
    assignment = {
        "reviewId": review_id,
        "reviewNonce": open_review["nonce"],
        "run": str(run),
        "cli": str(Path(__file__).resolve()),
        "language": manifest["language"],
        "reviewerTaskId": review.get("taskId"),
        "authorityHead": authority["head"],
        "source": str(run / "source.md"),
        "contract": str(run / "contract.md"),
        "envelope": str(run / "envelope.md"),
        "amendments": str(run / "amendments"),
        "phases": str(run / "phases"),
        "outcome": str(run / "outcome.md"),
        "outcomeSha256": outcome_digest,
        "probeRoot": str(probe_root),
        "maxProbeSeconds": 600,
        "previousVerdict": previous.get("verdict") if previous else None,
        "remediationPhases": remediation_phases,
    }
    return _result(
        "review.open", f"Opened convergence review {review_id}.", data=assignment
    )


def _probe_limits(timeout_seconds: int) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (timeout_seconds + 2, timeout_seconds + 4))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024, 16 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))


@contextmanager
def _probe_lock(run: Path):
    lock_path = _run_file(run, "reviews/.probe.lock")
    _require_regular_file(lock_path)
    with lock_path.open("r+", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _probe_identity(
    manifest: dict[str, Any], args: argparse.Namespace
) -> dict[str, Any]:
    _require_status(manifest, "run a review probe", {"reviewing"})
    review = manifest["review"]
    opened = review.get("open")
    task_id = review.get("taskId")
    if not isinstance(opened, dict) or opened.get("id") != args.review_id:
        raise IntegrityError("probe request does not match the open review")
    if opened.get("nonce") != args.review_nonce:
        raise IntegrityError("probe request has the wrong review nonce")
    if not task_id or opened.get("taskId") != task_id or task_id != args.task_id:
        raise IntegrityError("probe request is not owned by the attested reviewer task")
    return opened


def _read_tail(stream: Any, limit: int = 50_000) -> tuple[str, bool]:
    stream.flush()
    size = stream.tell()
    stream.seek(max(0, size - limit))
    return stream.read().decode("utf-8", errors="replace"), size > limit


def _process_token(pid: int) -> str:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
        return fields[21] if len(fields) > 21 else ""
    except (OSError, UnicodeError):
        return ""


def _reservation_index(opened: dict[str, Any], probe_id: str) -> int:
    for index, reservation in enumerate(opened["probeInFlight"]):
        if isinstance(reservation, dict) and reservation.get("id") == probe_id:
            return index
    return -1


def _release_probe_reservation(
    run: Path, args: argparse.Namespace, probe_id: str
) -> None:
    with _probe_lock(run):
        manifest = _load_manifest(run)
        opened = _probe_identity(manifest, args)
        index = _reservation_index(opened, probe_id)
        if index >= 0:
            opened["probeInFlight"].pop(index)
            _save_manifest(run, manifest)


def command_review_recover(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    if not args.reason.strip():
        raise UsageError("probe recovery reason must be non-empty")
    recovered: list[dict[str, Any]] = []
    created_paths: list[Path] = []
    with _probe_lock(run):
        manifest = _load_manifest(run)
        _require_status(manifest, "recover review probes", {"reviewing"})
        opened = manifest["review"].get("open")
        if not isinstance(opened, dict) or opened.get("id") != args.review_id:
            raise IntegrityError("probe recovery does not match the open review")
        if opened.get("nonce") != args.review_nonce:
            raise IntegrityError("probe recovery has the wrong review nonce")
        now = time.time()
        retained: list[dict[str, Any]] = []
        for reservation in opened["probeInFlight"]:
            owner_pid = reservation["ownerPid"]
            owner_start = reservation["ownerStart"]
            same_process = _process_token(owner_pid) == owner_start
            if same_process or now <= reservation["deadlineEpoch"]:
                retained.append(reservation)
                continue
            probe_id = reservation["id"]
            relative = f"reviews/probes/{args.review_id}/{probe_id}.json"
            record_path = _run_file(run, relative)
            record = {
                "schemaVersion": 1,
                "reviewId": args.review_id,
                "taskId": manifest["review"].get("taskId"),
                "status": "aborted",
                "reason": args.reason.strip(),
                "reservedAt": reservation["reservedAt"],
                "recoveredAt": _utc_now(),
                "timeoutSeconds": reservation["timeoutSeconds"],
                "chargedSeconds": reservation["timeoutSeconds"],
                "timedOut": True,
                "exitCode": None,
                "stdout": "",
                "stderr": "Reviewer host process ended before this probe could be recorded.",
                "stdoutTruncated": False,
                "stderrTruncated": False,
            }
            _write_json(record_path, record, replace=False)
            created_paths.append(record_path)
            identity = {
                "id": probe_id,
                "path": relative,
                "sha256": _sha256(record_path),
                "durationSeconds": 0,
                "chargedSeconds": reservation["timeoutSeconds"],
                "exitCode": None,
                "timedOut": True,
                "recovered": True,
            }
            opened["probes"].append(identity)
            recovered.append(identity)
        if not recovered:
            raise NotReadyError("no expired probe reservation is safe to recover")
        opened["probeInFlight"] = retained
        try:
            _save_manifest(run, manifest)
        except Exception:
            for created in created_paths:
                created.unlink(missing_ok=True)
            raise
    return _result(
        "review.recover",
        f"Recovered {len(recovered)} abandoned review probe reservation(s).",
        data={"probes": recovered},
    )


def command_review_probe(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    _validate_run(run, _load_manifest(run))
    if not args.command:
        raise UsageError("review probe requires a command after --")
    if args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        raise UsageError("review probe requires a command after --")
    timeout_seconds = args.timeout_seconds
    if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= 600:
        raise UsageError("probe timeout must be between 1 and 600 seconds")
    bubblewrap = Path("/usr/bin/bwrap")
    try:
        bwrap_info = bubblewrap.stat()
    except OSError as error:
        raise LocalError(
            "trusted /usr/bin/bwrap is required for review probes; no unsafe fallback"
        ) from error
    if (
        not bubblewrap.is_file()
        or bubblewrap.is_symlink()
        or bwrap_info.st_uid != 0
        or bwrap_info.st_mode & 0o022
    ):
        raise LocalError("bubblewrap is required for review probes; no unsafe fallback")

    with _probe_lock(run):
        reserved_manifest = _load_manifest(run)
        opened = _probe_identity(reserved_manifest, args)
        remaining = 600 - opened["probeUsedSeconds"]
        if timeout_seconds > remaining:
            raise NotReadyError(
                f"probe requests {timeout_seconds}s but only {remaining}s remain"
            )
        probe_id = f"probe-{opened['probeNext']:04d}"
        opened["probeNext"] += 1
        opened["probeUsedSeconds"] += timeout_seconds
        opened["probeInFlight"].append(
            {
                "id": probe_id,
                "ownerPid": os.getpid(),
                "ownerStart": _process_token(os.getpid())
                or f"unknown-{time.time_ns()}",
                "reservedAt": _utc_now(),
                "deadlineEpoch": time.time() + timeout_seconds + 30,
                "timeoutSeconds": timeout_seconds,
            }
        )
        _save_manifest(run, reserved_manifest)

    probe_root = _run_file(run, opened["probeRoot"])
    _require_regular_file(_run_file(run, "manifest.json"))
    if probe_root.is_symlink() or not probe_root.is_dir():
        _release_probe_reservation(run, args, probe_id)
        raise IntegrityError("review probe root must be a non-symlink directory")
    probe_root = probe_root.resolve()
    command = [
        str(bubblewrap),
        "--die-with-parent",
        "--new-session",
        "--unshare-all",
        "--ro-bind",
        "/",
        "/",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--tmpfs",
        "/run",
        "--bind",
        str(probe_root),
        str(probe_root),
        "--chdir",
        str(probe_root),
        "--clearenv",
        "--setenv",
        "HOME",
        "/tmp",
        "--setenv",
        "TMPDIR",
        "/tmp",
        "--setenv",
        "PATH",
        os.environ.get("PATH", "/usr/bin:/bin"),
        "--",
        *args.command,
    ]
    started_at = _utc_now()
    started = time.monotonic()
    try:
        with (
            tempfile.TemporaryFile() as stdout_file,
            tempfile.TemporaryFile() as stderr_file,
        ):
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                start_new_session=True,
                preexec_fn=lambda: _probe_limits(timeout_seconds),
            )
            timed_out = False
            try:
                process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            stdout, stdout_truncated = _read_tail(stdout_file)
            stderr, stderr_truncated = _read_tail(stderr_file)
        duration = max(1, math.ceil(time.monotonic() - started))
        if process.returncode != 0 and stderr.lstrip().startswith("bwrap:"):
            raise LocalError(
                "bubblewrap is installed but unavailable in this host sandbox; no unsafe fallback was used"
            )

        relative = f"reviews/probes/{args.review_id}/{probe_id}.json"
        record_path = _run_file(run, relative)
        record = {
            "schemaVersion": 1,
            "reviewId": args.review_id,
            "taskId": args.task_id,
            "command": args.command,
            "startedAt": started_at,
            "finishedAt": _utc_now(),
            "durationSeconds": duration,
            "timeoutSeconds": timeout_seconds,
            "chargedSeconds": timeout_seconds,
            "timedOut": timed_out,
            "exitCode": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdoutTruncated": stdout_truncated,
            "stderrTruncated": stderr_truncated,
        }
        _write_json(record_path, record, replace=False)
        probe_identity = {
            "id": probe_id,
            "path": relative,
            "sha256": _sha256(record_path),
            "durationSeconds": duration,
            "chargedSeconds": timeout_seconds,
            "exitCode": process.returncode,
            "timedOut": timed_out,
        }
        with _probe_lock(run):
            latest = _load_manifest(run)
            latest_opened = _probe_identity(latest, args)
            reservation_index = _reservation_index(latest_opened, probe_id)
            if reservation_index < 0:
                raise IntegrityError("review probe reservation disappeared")
            latest_opened["probeInFlight"].pop(reservation_index)
            latest_opened["probes"].append(probe_identity)
            _save_manifest(run, latest)
    except Exception:
        _release_probe_reservation(run, args, probe_id)
        if "record_path" in locals():
            record_path.unlink(missing_ok=True)
        raise
    return _result(
        "review.probe",
        "Review probe completed inside the read-only sandbox.",
        data={
            **probe_identity,
            "stdout": record["stdout"],
            "stderr": record["stderr"],
            "stdoutTruncated": record["stdoutTruncated"],
            "stderrTruncated": record["stderrTruncated"],
        },
    )


def _read_explicit_input(args: argparse.Namespace) -> str:
    if bool(args.stdin) == bool(args.from_file):
        raise UsageError("choose exactly one of --stdin or --from")
    if args.stdin:
        content = sys.stdin.read(MAX_EXPLICIT_INPUT_BYTES + 1)
    else:
        path = Path(args.from_file).expanduser().resolve()
        _require_regular_file(path)
        if path.stat().st_size > MAX_EXPLICIT_INPUT_BYTES:
            raise UsageError(f"review input exceeds {MAX_EXPLICIT_INPUT_BYTES} bytes")
        content = path.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) > MAX_EXPLICIT_INPUT_BYTES:
        raise UsageError(f"review input exceeds {MAX_EXPLICIT_INPUT_BYTES} bytes")
    return content


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise UsageError(f"review field {field} must be an array of non-empty strings")
    return [item.strip() for item in value]


def _validate_review_claim(
    raw: str, expected: dict[str, str] | None = None
) -> dict[str, Any]:
    try:
        claim = json.loads(raw)
    except json.JSONDecodeError as error:
        raise UsageError(f"review input must be JSON: {error}") from error
    if not isinstance(claim, dict) or claim.get("schemaVersion") != 1:
        raise UsageError("review must declare schemaVersion 1")
    verdict = claim.get("verdict")
    if verdict not in {"approved", "rejected", "blocked"}:
        raise UsageError("review verdict must be approved, rejected, or blocked")
    if not isinstance(claim.get("summary"), str) or not claim["summary"].strip():
        raise UsageError("review summary must be non-empty")
    criteria = claim.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise UsageError("review criteria must be a non-empty array")
    normalized_criteria = []
    for index, item in enumerate(criteria):
        if not isinstance(item, dict):
            raise UsageError(f"review criterion {index} must be an object")
        result = item.get("result")
        if result not in {"satisfied", "unsatisfied", "uncertain"}:
            raise UsageError(f"review criterion {index} has an invalid result")
        criterion = item.get("criterion")
        reason = item.get("reason")
        if (
            not isinstance(criterion, str)
            or not criterion.strip()
            or not isinstance(reason, str)
            or not reason.strip()
        ):
            raise UsageError(f"review criterion {index} needs criterion and reason")
        normalized_criteria.append(
            {
                "criterion": criterion.strip(),
                "result": result,
                "evidence": _string_list(
                    item.get("evidence", []), f"criteria[{index}].evidence"
                ),
                "reason": reason.strip(),
            }
        )
    normalized = {
        "schemaVersion": 1,
        "reviewId": claim.get("reviewId"),
        "reviewNonce": claim.get("reviewNonce"),
        "reviewerTaskId": claim.get("reviewerTaskId"),
        "authorityHead": claim.get("authorityHead"),
        "outcomeSha256": claim.get("outcomeSha256"),
        "verdict": verdict,
        "summary": claim["summary"].strip(),
        "criteria": normalized_criteria,
        "evidenceInspected": _string_list(
            claim.get("evidenceInspected", []), "evidenceInspected"
        ),
        "probes": _string_list(claim.get("probes", []), "probes"),
        "counterevidence": _string_list(
            claim.get("counterevidence", []), "counterevidence"
        ),
        "requiredActions": _string_list(
            claim.get("requiredActions", []), "requiredActions"
        ),
        "knownLimitations": _string_list(
            claim.get("knownLimitations", []), "knownLimitations"
        ),
        "confidence": claim.get("confidence"),
    }
    if normalized["confidence"] not in {"high", "medium", "low"}:
        raise UsageError("review confidence must be high, medium, or low")
    if not isinstance(normalized["reviewId"], str) or not ITEM_ID_PATTERN.fullmatch(
        normalized["reviewId"]
    ):
        raise UsageError("reviewId must be an R#### identity")
    if not isinstance(normalized["reviewNonce"], str) or not re.fullmatch(
        r"[0-9a-f]{32}", normalized["reviewNonce"]
    ):
        raise UsageError("reviewNonce must be the assigned 128-bit nonce")
    if not isinstance(
        normalized["reviewerTaskId"], str
    ) or not TASK_ID_PATTERN.fullmatch(normalized["reviewerTaskId"]):
        raise UsageError("reviewerTaskId must be the attested reviewer task")
    for field in ("authorityHead", "outcomeSha256"):
        if not isinstance(normalized[field], str) or not SHA256_PATTERN.fullmatch(
            normalized[field]
        ):
            raise UsageError(f"review {field} must be a SHA-256 digest")
    if expected:
        mismatched = [
            field for field, value in expected.items() if normalized.get(field) != value
        ]
        if mismatched:
            raise IntegrityError(
                "review verdict does not match its assignment: " + ", ".join(mismatched)
            )
    if verdict == "approved":
        if any(item["result"] != "satisfied" for item in normalized_criteria):
            raise UsageError(
                "an approved review cannot contain unsatisfied or uncertain criteria"
            )
        if any(not item["evidence"] for item in normalized_criteria):
            raise UsageError("every approved criterion must cite non-empty evidence")
        if normalized["requiredActions"]:
            raise UsageError("an approved review cannot contain requiredActions")
    return normalized


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- None."


def _review_markdown(
    review_id: str, opened: dict[str, Any], task_id: str, claim: dict[str, Any]
) -> str:
    criteria = []
    for item in claim["criteria"]:
        criteria.extend(
            [
                f"### {item['criterion']}",
                f"- Result: `{item['result']}`",
                f"- Reason: {item['reason']}",
                "- Evidence:",
                _bullets(item["evidence"]),
            ]
        )
    raw = json.dumps(claim, ensure_ascii=False, sort_keys=True, indent=2)
    blocks = [
        f"# Autopilot Review {review_id}",
        f"- Verdict: `{claim['verdict']}`",
        f"- Confidence: `{claim['confidence']}`",
        f"- Reviewer task: `{task_id}`",
        f"- Authority head: `{opened['authorityHead']}`",
        f"- Outcome SHA-256: `{opened['outcomeSha256']}`",
        "## Summary",
        claim["summary"],
        "## Contract Criteria",
        "\n\n".join(criteria),
        "## Evidence Inspected",
        _bullets(claim["evidenceInspected"]),
        "## Probes",
        _bullets(claim["probes"]),
        "## Counterevidence",
        _bullets(claim["counterevidence"]),
        "## Required Actions",
        _bullets(claim["requiredActions"]),
        "## Known Limitations",
        _bullets(claim["knownLimitations"]),
        "## Structured Verdict",
        f"```json\n{raw}\n```",
    ]
    return "\n\n".join(blocks) + "\n"


def _stored_review_claim(path: Path) -> dict[str, Any]:
    _require_regular_file(path)
    text = path.read_text(encoding="utf-8")
    matches = re.findall(r"```json\s*([\s\S]*?)\s*```", text)
    if len(matches) != 1:
        raise IntegrityError(f"review must contain one structured verdict: {path}")
    try:
        return _validate_review_claim(matches[0])
    except UsageError as error:
        raise IntegrityError(f"stored review verdict is invalid: {error}") from error


def command_review_record(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    raw_claim = _read_explicit_input(args)
    with _probe_lock(run):
        manifest = _load_manifest(run)
        _require_status(manifest, "record a review", {"reviewing"})
        authority = _verify_authority(run, manifest)
        review = manifest["review"]
        opened = review.get("open")
        task_id = review.get("taskId")
        if not isinstance(opened, dict):
            raise NotReadyError("no convergence review is open")
        if not isinstance(task_id, str) or not task_id:
            raise NotReadyError(
                "the reviewer must attest its task identity before recording a verdict"
            )
        if opened.get("probeInFlight"):
            raise NotReadyError(
                "recover or finish every reserved review probe before recording a verdict"
            )
        if opened.get("taskId") != task_id:
            raise IntegrityError(
                "open review is not bound to the run reviewer identity"
            )
        if opened.get("authorityHead") != authority["head"]:
            raise IntegrityError("authority changed while the review was open")
        if opened.get("outcomeSha256") != _sha256(_run_file(run, "outcome.md")):
            raise IntegrityError(
                "outcome changed while the review was open; open a new review"
            )
        expected = {
            "reviewId": opened["id"],
            "reviewNonce": opened["nonce"],
            "reviewerTaskId": task_id,
            "authorityHead": opened["authorityHead"],
            "outcomeSha256": opened["outcomeSha256"],
        }
        claim = _validate_review_claim(raw_claim, expected)
        relative = f"reviews/{opened['id']}.md"
        content = _review_markdown(opened["id"], opened, task_id, claim)
        destination = _run_file(run, relative)
        _atomic_write(destination, content, replace=False)
        digest = _sha256(destination)
        record = {
            "id": opened["id"],
            "path": relative,
            "sha256": digest,
            "verdict": claim["verdict"],
            "confidence": claim["confidence"],
            "authorityHead": opened["authorityHead"],
            "outcomeSha256": opened["outcomeSha256"],
            "taskId": task_id,
            "reviewNonce": opened["nonce"],
            "closedPhaseCount": opened["closedPhaseCount"],
            "recordedAt": _utc_now(),
        }
        try:
            review["records"].append(record)
            review["next"] += 1
            review["open"] = None
            manifest["status"] = {
                "approved": "review-approved",
                "rejected": "review-rejected",
                "blocked": "blocked",
            }[claim["verdict"]]
            _save_manifest(run, manifest)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return _result(
        "review.record",
        f"Recorded {claim['verdict']} review {record['id']}.",
        data=record,
    )


def command_review_list(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    _validate_reviews(run, manifest)
    return _result(
        "review.list",
        f"{len(manifest['review']['records'])} recorded review(s).",
        data={
            "taskId": manifest["review"]["taskId"],
            "open": manifest["review"]["open"],
            "records": manifest["review"]["records"],
        },
    )


def command_goal_render(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    manifest = _load_manifest(run)
    _require_status(manifest, "render a Goal projection", {"active"})
    authority = _verify_authority(run, manifest)
    current = manifest["phase"].get("current")
    if not isinstance(current, dict):
        raise NotReadyError("open a semantic phase before rendering a Goal projection")
    contract = _require_fields(run, "contract.md", "contract", CONTRACT_FIELDS)
    envelope = _require_fields(run, "envelope.md", "envelope", ENVELOPE_FIELDS)
    phase = _require_fields(run, "phases/current.md", "phase", PHASE_FIELDS[:5])
    objective = "\n".join(
        [
            f"Autopilot run: {manifest['runId']}",
            f"Autopilot dossier: {run}",
            f"Overall intent: {contract['intent']}",
            f"Failure boundary: {contract['failure_boundary']}",
            f"Human gates: {contract['human_gates']}",
            f"Authority: {run / 'contract.md'} @ {authority['files']['contract.md']}; amendment head {authority['head']}",
            f"Current semantic phase {current['id']}: {phase['objective']}",
            f"Exit evidence: {phase['exit_evidence']}",
            f"Phase record: {run / 'phases/current.md'}",
            "At phase exit, validate the dossier, re-read effective authority, close the phase, select the next semantic phase, and update this objective. Complete the Goal only when the overall contract is satisfied.",
        ]
    )
    success = "\n".join(
        [
            contract["success_boundary"],
            f"The effective authority is contract.md plus sealed amendments at head {authority['head']}.",
        ]
    )
    constraints = "\n".join(
        [
            f"Fixed decisions: {contract['fixed_decisions']}",
            f"Non-goals: {contract['non_goals']}",
            f"Execution authorization: {run / 'envelope.md'} @ {authority['files']['envelope.md']}.",
            f"Write boundary: {envelope['write_scope']}",
            f"Stop conditions: {envelope['stop_conditions']}",
            f"External side effects: {envelope['side_effects']}",
            "Do not alter sealed authority outside an explicitly authorized amendment.",
        ]
    )
    limits = {
        "objective": (objective, MAX_OBJECTIVE_LENGTH),
        "successCriteria": (success, MAX_META_LENGTH),
        "constraints": (constraints, MAX_META_LENGTH),
    }
    exceeded = [
        f"{name}={len(value)}/{limit}"
        for name, (value, limit) in limits.items()
        if len(value) > limit
    ]
    if exceeded:
        raise NotReadyError(
            "Goal projection exceeds plugin limits: " + ", ".join(exceeded)
        )
    projection = {name: value for name, (value, _limit) in limits.items()}
    projection["mode"] = "normal"
    projection["maxTurns"] = int(envelope["max_turns"])
    projection["maxDurationMs"] = int(envelope["max_duration_ms"])
    projection["maxTokens"] = int(envelope["max_tokens"])
    return _result("goal.render", "Goal projection rendered.", data=projection)


def command_run_finalize(args: argparse.Namespace) -> dict[str, Any]:
    run = _discover_run(args.run)
    with _probe_lock(run):
        manifest = _load_manifest(run)
        authority = _verify_authority(run, manifest)
        _require_quiet_boundary(manifest, "finalize the run", {"review-approved"})
        _validate_run(run, manifest)
        if not manifest["phase"]["closed"]:
            raise NotReadyError("cannot finalize without a closed semantic phase")
        _validate_outcome(run)
        records = manifest["review"].get("records", [])
        if not records or records[-1].get("verdict") != "approved":
            raise NotReadyError("the latest convergence review must be approved")
        latest = records[-1]
        outcome_digest = _sha256(_run_file(run, "outcome.md"))
        if latest.get("authorityHead") != authority["head"]:
            raise IntegrityError("approved review targets an obsolete authority head")
        if latest.get("outcomeSha256") != outcome_digest:
            raise IntegrityError("outcome changed after the approved review")
        manifest["status"] = "finalized"
        manifest["outcome"] = {"sha256": outcome_digest, "finalizedAt": _utc_now()}
        _save_manifest(run, manifest)
    return _result(
        "run.finalize",
        "Autopilot run finalized and ready for goal_complete.",
        data={"outcomeSha256": outcome_digest, "reviewId": latest["id"]},
    )


def _add_run_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--run",
        help="Run directory; defaults to the nearest ancestor containing manifest.json.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit one compact versioned JSON object on stdout.",
    )


def _leaf(
    group: argparse._SubParsersAction, name: str, help_text: str, handler: Any
) -> argparse.ArgumentParser:
    parser = group.add_parser(
        name,
        help=help_text,
        description=help_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    command = " ".join(parser.prog.split()[1:])
    example = LEAF_EXAMPLES.get(command)
    if example:
        parser.epilog = f"Example:\n  {example}"
    parser.set_defaults(handler=handler)
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="labflow-autopilot",
        description="Create, seal, validate, review, and finalize one semantic Autopilot run dossier.",
    )
    parser.add_argument("--version", action="version", version="labflow-autopilot 1")
    groups = parser.add_subparsers(dest="group", required=True)

    run = groups.add_parser("run", help="Manage run identity and finalization.")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    init = _leaf(
        run_commands,
        "init",
        "Create a new non-overwriting Autopilot run dossier.",
        command_run_init,
    )
    init.add_argument("--root", help="Topic root; defaults to the current Git root.")
    init.add_argument(
        "--title",
        required=True,
        help="Human run title used to derive the default semantic slug.",
    )
    init.add_argument("--slug", help="Optional lowercase ASCII run slug.")
    init.add_argument(
        "--language", default="en", help="Document language, such as en or zh-CN."
    )
    init.add_argument(
        "--stdin",
        action="store_true",
        help="Read the approved plan from stdin; never implicit.",
    )
    init.add_argument(
        "--json",
        action="store_true",
        help="Emit one compact versioned JSON object on stdout.",
    )
    for name, description, handler in (
        ("status", "Show one run's compact lifecycle state.", command_run_status),
        (
            "validate",
            "Pure-read validation of dossier structure and sealed identities.",
            command_run_validate,
        ),
        (
            "finalize",
            "Finalize an outcome only after a matching approved review.",
            command_run_finalize,
        ),
    ):
        command = _leaf(run_commands, name, description, handler)
        _add_run_argument(command)
    resume = _leaf(
        run_commands,
        "resume",
        "Explicitly resume a blocked run after its external requirement is resolved.",
        command_run_resume,
    )
    _add_run_argument(resume)
    resume.add_argument(
        "--reason", required=True, help="Concrete reason the blocked run may resume."
    )

    authority = groups.add_parser(
        "authority", help="Seal or verify immutable run authority."
    )
    authority_commands = authority.add_subparsers(
        dest="authority_command", required=True
    )
    for name, description, handler in (
        (
            "seal",
            "Seal source, contract, and envelope as one authority identity.",
            command_authority_seal,
        ),
        (
            "verify",
            "Verify every authority digest and amendment-chain link.",
            command_authority_verify,
        ),
    ):
        command = _leaf(authority_commands, name, description, handler)
        _add_run_argument(command)

    amendment = groups.add_parser(
        "amendment", help="Manage explicitly user-authorized semantic amendments."
    )
    amendment_commands = amendment.add_subparsers(
        dest="amendment_command", required=True
    )
    amendment_new = _leaf(
        amendment_commands,
        "new",
        "Create the next amendment draft.",
        command_amendment_new,
    )
    _add_run_argument(amendment_new)
    amendment_new.add_argument("--title", required=True, help="Human amendment title.")
    amendment_new.add_argument("--slug", help="Optional amendment filename slug.")
    for name, description, handler in (
        (
            "seal",
            "Validate and append the open amendment to the authority hash chain.",
            command_amendment_seal,
        ),
        (
            "list",
            "List sealed amendments and the effective authority head.",
            command_amendment_list,
        ),
    ):
        command = _leaf(amendment_commands, name, description, handler)
        _add_run_argument(command)

    phase = groups.add_parser(
        "phase",
        help="Manage adaptive semantic phases without prescribing implementation TODOs.",
    )
    phase_commands = phase.add_subparsers(dest="phase_command", required=True)
    phase_open = _leaf(
        phase_commands,
        "open",
        "Open the next semantic phase draft.",
        command_phase_open,
    )
    _add_run_argument(phase_open)
    phase_open.add_argument(
        "--title", required=True, help="Human semantic phase title."
    )
    phase_close = _leaf(
        phase_commands,
        "close",
        "Validate, number, and seal the current semantic phase.",
        command_phase_close,
    )
    _add_run_argument(phase_close)
    phase_close.add_argument("--slug", help="Optional closed phase filename slug.")
    phase_list = _leaf(
        phase_commands,
        "list",
        "List current and sealed semantic phases.",
        command_phase_list,
    )
    _add_run_argument(phase_list)

    review = groups.add_parser(
        "review", help="Attest one persistent reviewer and record convergence verdicts."
    )
    review_commands = review.add_subparsers(dest="review_command", required=True)
    review_open = _leaf(
        review_commands,
        "open",
        "Allocate a review identity and bounded probe root.",
        command_review_open,
    )
    _add_run_argument(review_open)
    review_probe = _leaf(
        review_commands,
        "probe",
        "Run one cumulative-budgeted command in a read-only bubblewrap sandbox.",
        command_review_probe,
    )
    _add_run_argument(review_probe)
    review_probe.add_argument(
        "--review-id", required=True, help="Open R#### review identity."
    )
    review_probe.add_argument(
        "--review-nonce", required=True, help="Nonce returned by review open."
    )
    review_probe.add_argument(
        "--task-id", required=True, help="Attested reviewer task ID."
    )
    review_probe.add_argument(
        "--timeout-seconds",
        type=int,
        required=True,
        help="Hard wall timeout, bounded by the 600-second review budget.",
    )
    review_probe.add_argument(
        "command", nargs=argparse.REMAINDER, help="Command and arguments after --."
    )
    review_recover = _leaf(
        review_commands,
        "recover",
        "Recover only expired probe reservations whose owner process has ended.",
        command_review_recover,
    )
    _add_run_argument(review_recover)
    review_recover.add_argument(
        "--review-id", required=True, help="Open R#### review identity."
    )
    review_recover.add_argument(
        "--review-nonce", required=True, help="Nonce returned by review open."
    )
    review_recover.add_argument(
        "--reason", required=True, help="Auditable reason the probe owner ended."
    )
    review_record = _leaf(
        review_commands,
        "record",
        "Validate and record one structured reviewer verdict.",
        command_review_record,
    )
    _add_run_argument(review_record)
    source = review_record.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--stdin", action="store_true", help="Read the reviewer JSON from stdin."
    )
    source.add_argument(
        "--from", dest="from_file", help="Read the reviewer JSON from one regular file."
    )
    review_list = _leaf(
        review_commands,
        "list",
        "List the persistent reviewer identity and recorded verdicts.",
        command_review_list,
    )
    _add_run_argument(review_list)

    goal = groups.add_parser(
        "goal", help="Render a bounded Goal projection from sealed semantic state."
    )
    goal_commands = goal.add_subparsers(dest="goal_command", required=True)
    goal_render = _leaf(
        goal_commands,
        "render",
        "Render objective, successCriteria, constraints, and mode.",
        command_goal_render,
    )
    _add_run_argument(goal_render)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args)
        _emit(payload, as_json=bool(getattr(args, "json", False)))
        return EXIT_OK
    except CliError as error:
        group = getattr(args, "group", "unknown")
        operation = f"{group}.{getattr(args, f'{group}_command', 'unknown')}"
        payload = {
            "version": 1,
            "operation": operation,
            "ok": False,
            "error": error.__class__.__name__,
            "message": str(error),
        }
        if getattr(args, "json", False):
            print(
                json.dumps(
                    payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
            )
        else:
            print(f"labflow-autopilot: {error}", file=sys.stderr)
        return error.exit_code
    except (OSError, UnicodeError) as error:
        print(f"labflow-autopilot: local I/O failure: {error}", file=sys.stderr)
        return EXIT_LOCAL


if __name__ == "__main__":
    raise SystemExit(main())
