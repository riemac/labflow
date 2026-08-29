#!/usr/bin/env python3
"""Create and validate local learning-forensics case dossiers.

The helper owns deterministic filesystem mechanics only. It does not inspect a
training run, form a hypothesis, execute a probe, or modify project source.
Scientific interpretation remains with the coordinator and learning workers.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Sequence


VISIBLE_FILES = ("README.md", "overview.md", "topics/README.md")
HIDDEN_DIRECTORIES = (
    ".learning/cases",
    ".learning/audit/lanes",
    ".learning/probes",
    ".learning/state",
)
DOSSIER_GITIGNORE = "*\n"
CASE_PATTERN = re.compile(r"case-(\d{4})\.md$")
PROBE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
CASE_REQUIRED_SECTIONS = (
    "Case Identity",
    "Decision To Support",
    "Frozen Observations",
    "Case-Specific Causal Chain",
    "Authoritative Design Sources",
    "Available Evidence",
    "Withheld Diagnosis Sources",
    "Constraints And Safety",
    "Missing Facts",
)
PROBE_REQUIRED_SECTIONS = (
    "Hypothesis",
    "Prediction If True",
    "Prediction If False",
    "Inputs And Frozen Evidence",
    "Changed And Controlled Variables",
    "Evaluation Measure",
    "Stop Conditions",
)


class CaseError(ValueError):
    """Reject destructive, ambiguous, or structurally invalid operations."""


def _today() -> str:
    """Return the UTC date used in stable dossier frontmatter."""

    return datetime.now(timezone.utc).date().isoformat()


def _root(value: str | Path) -> Path:
    """Resolve a non-empty dossier path without requiring it to exist."""

    raw = str(value)
    if not raw or "\x00" in raw:
        raise CaseError("case root is invalid")
    return Path(raw).expanduser().resolve()


def _frontmatter(*, language: str, title: str, kind: str, question: str | None = None) -> str:
    """Build conservative YAML using JSON-compatible quoted scalar values."""

    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"kind: {json.dumps(kind)}",
        f"language: {json.dumps(language)}",
        f"updated: {_today()}",
    ]
    if question:
        lines.append(f"question: {json.dumps(question, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def _skeleton(*, language: str, title: str, question: str | None) -> dict[str, str]:
    """Return minimal human and hidden entry files without synthesizing findings."""

    chinese = language.lower().startswith("zh")
    question_text = question or ("开始调查前明确有界问题。" if chinese else "State the bounded question before investigation.")
    if chinese:
        return {
            ".gitignore": DOSSIER_GITIGNORE,
            "README.md": "# 学习系统取证\n\n- [当前概览](overview.md)\n- [专题报告](topics/)\n- `assets/`：可选图、表和示意图。\n",
            "overview.md": f"{_frontmatter(language=language, title=title, kind='learning-overview', question=question)}\n\n# 当前概览\n\n## 问题\n\n{question_text}\n\n> [!abstract] 当前结论\n> 尚未综合。\n\n## 关键证据\n\n待整理。\n\n> [!question] 重大未决问题\n> 待整理。\n",
            "topics/README.md": "# 专题报告\n\n每个文件是主代理核验并综合后形成的一篇可独立阅读报告；不要在此保存 worker 原始日志。\n",
            ".learning/brief.md": f"{_frontmatter(language=language, title=title, kind='learning-brief', question=question)}\n\n# Learning Brief\n\n## Bounded Question\n\n{question_text}\n\n## Decision To Support\n\n待填写。\n\n## Safety Boundary\n\n待填写。\n",
            ".learning/evidence-index.yaml": "schema_version: 1.0.0\nevidence: []\n",
            ".learning/decision-tree.md": "# Agent Decision Tree\n\n尚未建立。\n",
            ".learning/record.md": "# Agent Record\n\n尚未记录。\n",
            ".learning/audit/cross-examination.md": "# Cross-Examination\n\n尚未综合。\n",
            ".learning/state/workers.json": '{"schema_version":"1.0.0","workers":[]}\n',
            ".learning/state/processes.json": '{"schema_version":"1.0.0","processes":[]}\n',
        }
    return {
        ".gitignore": DOSSIER_GITIGNORE,
        "README.md": "# Learning Forensics\n\n- [Current overview](overview.md)\n- [Topic reports](topics/)\n- `assets/`: optional figures, tables, and diagrams.\n",
        "overview.md": f"{_frontmatter(language=language, title=title, kind='learning-overview', question=question)}\n\n# Current Overview\n\n## Question\n\n{question_text}\n\n> [!abstract] Current answer\n> Not synthesized yet.\n\n## Decisive Evidence\n\nTo be curated.\n\n> [!question] Major unresolved question\n> To be curated.\n",
        "topics/README.md": "# Topic Reports\n\nEach file is a coordinator-verified standalone report; do not store raw worker narration here.\n",
        ".learning/brief.md": f"{_frontmatter(language=language, title=title, kind='learning-brief', question=question)}\n\n# Learning Brief\n\n## Bounded Question\n\n{question_text}\n\n## Decision To Support\n\nTo be completed.\n\n## Safety Boundary\n\nTo be completed.\n",
        ".learning/evidence-index.yaml": "schema_version: 1.0.0\nevidence: []\n",
        ".learning/decision-tree.md": "# Agent Decision Tree\n\nNot established yet.\n",
        ".learning/record.md": "# Agent Record\n\nNo entries yet.\n",
        ".learning/audit/cross-examination.md": "# Cross-Examination\n\nNot synthesized yet.\n",
        ".learning/state/workers.json": '{"schema_version":"1.0.0","workers":[]}\n',
        ".learning/state/processes.json": '{"schema_version":"1.0.0","processes":[]}\n',
    }


def initialize(path: str | Path, *, language: str, title: str, question: str | None) -> Path:
    """Create a non-destructive human/audit dossier skeleton."""

    root = _root(path)
    files = _skeleton(language=language, title=title, question=question)
    conflicts = [relative for relative in files if (root / relative).exists()]
    if conflicts:
        raise CaseError("refusing to overwrite existing files: " + ", ".join(conflicts))
    root.mkdir(parents=True, exist_ok=True)
    for relative in HIDDEN_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return root


def _case_files(root: Path) -> list[Path]:
    """Return numbered case Markdown files in ascending numeric order."""

    cases: list[tuple[int, Path]] = []
    for path in (root / ".learning/cases").glob("case-*.md"):
        match = CASE_PATTERN.fullmatch(path.name)
        if match:
            cases.append((int(match.group(1)), path))
    return [path for _index, path in sorted(cases)]


def new_case(path: str | Path) -> Path:
    """Create the next unsealed fact-only casefile draft."""

    root = _root(path)
    cases_directory = root / ".learning/cases"
    if not cases_directory.is_dir():
        raise CaseError("case dossier is not initialized")
    existing = _case_files(root)
    next_index = int(existing[-1].stem.split("-")[-1]) + 1 if existing else 1
    destination = cases_directory / f"case-{next_index:04d}.md"
    content = f"""---
schema_version: 1.0.0
case_id: case-{next_index:04d}
status: draft
created: {_today()}
---

# Blind Casefile

## Case Identity

## Decision To Support

## Frozen Observations

## Case-Specific Causal Chain

## Authoritative Design Sources

## Available Evidence

## Withheld Diagnosis Sources

## Constraints And Safety

## Missing Facts
"""
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(content)
    return destination


def _case_path(root: Path, case_name: str) -> Path:
    """Resolve one numbered case name without allowing directory traversal."""

    if not CASE_PATTERN.fullmatch(case_name):
        raise CaseError("case must be a basename such as case-0001.md")
    path = root / ".learning/cases" / case_name
    if not path.is_file():
        raise CaseError(f"case file does not exist: {path}")
    return path


def _sha256(path: Path) -> str:
    """Return the exact byte-level SHA-256 identity of a casefile."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _frontmatter_value(text: str, name: str) -> str | None:
    """Read one simple scalar from the case/probe frontmatter."""

    match = re.search(rf"(?m)^{re.escape(name)}:\s*[\"']?([^\"'\n]+)", text)
    return match.group(1).strip() if match else None


def _section_bodies(text: str) -> dict[str, str]:
    """Return second-level Markdown section bodies keyed by heading text."""

    matches = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", text))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1).strip()] = text[match.end() : end].strip()
    return result


def _case_errors(case_path: Path, *, expected_status: str | None = None) -> list[str]:
    """Validate the identity and fact-bearing structure of one casefile."""

    text = case_path.read_text(encoding="utf-8")
    errors: list[str] = []
    expected_id = case_path.stem
    if _frontmatter_value(text, "schema_version") != "1.0.0":
        errors.append(f"case {case_path.name} must declare schema_version 1.0.0")
    if _frontmatter_value(text, "case_id") != expected_id:
        errors.append(f"case {case_path.name} has a mismatched case_id")
    status = _frontmatter_value(text, "status")
    if status not in {"draft", "sealed"}:
        errors.append(f"case {case_path.name} has invalid status={status!r}")
    if expected_status is not None and status != expected_status:
        errors.append(f"case {case_path.name} must have status={expected_status}")
    sections = _section_bodies(text)
    require_content = expected_status is not None or status == "sealed"
    for heading in CASE_REQUIRED_SECTIONS:
        if heading not in sections:
            errors.append(f"case {case_path.name} is missing section: {heading}")
        elif require_content and not sections[heading]:
            errors.append(f"case {case_path.name} has an empty section: {heading}")
    forbidden = {"Hypotheses", "Diagnosis", "Root Cause", "Recommendations", "假设", "诊断", "根因", "建议"}
    for heading in sorted(forbidden & set(sections)):
        errors.append(f"blind case {case_path.name} contains diagnosis section: {heading}")
    return errors


def seal_case(path: str | Path, *, case_name: str) -> Path:
    """Validate one fact-bearing draft, mark it sealed, and write its digest."""

    root = _root(path)
    case_path = _case_path(root, case_name)
    sidecar = case_path.with_suffix(case_path.suffix + ".sha256")
    if sidecar.exists():
        _sealed_digest(case_path)
        return sidecar
    text = case_path.read_text(encoding="utf-8")
    status = _frontmatter_value(text, "status")
    if status == "draft":
        errors = _case_errors(case_path, expected_status="draft")
        if errors:
            raise CaseError("; ".join(errors))
        sealed = re.sub(r"(?m)^status:\s*draft\s*$", "status: sealed", text, count=1)
        temporary = case_path.with_name(f".{case_path.name}.sealing-{os.getpid()}")
        with temporary.open("x", encoding="utf-8") as stream:
            stream.write(sealed)
        temporary.replace(case_path)
    elif status != "sealed":
        raise CaseError(f"case {case_name} has invalid status={status!r}")
    errors = _case_errors(case_path, expected_status="sealed")
    if errors:
        raise CaseError("; ".join(errors))
    with sidecar.open("x", encoding="ascii") as stream:
        stream.write(f"{_sha256(case_path)}  {case_path.name}\n")
    return sidecar


def _sealed_digest(case_path: Path) -> str:
    """Read and verify the sealed digest required by a probe manifest."""

    errors = _case_errors(case_path, expected_status="sealed")
    if errors:
        raise CaseError("; ".join(errors))
    sidecar = case_path.with_suffix(case_path.suffix + ".sha256")
    if not sidecar.is_file():
        raise CaseError(f"case must be sealed before creating a probe: {case_path.name}")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = _sha256(case_path)
    if expected != actual:
        raise CaseError(f"sealed case hash mismatch: {case_path.name}")
    return expected


def new_probe(path: str | Path, *, probe_id: str, case_name: str) -> Path:
    """Create one isolated probe skeleton tied to a sealed case identity."""

    root = _root(path)
    if not PROBE_ID_PATTERN.fullmatch(probe_id):
        raise CaseError("probe id must be a lowercase path-safe identifier")
    case_path = _case_path(root, case_name)
    digest = _sealed_digest(case_path)
    probe_root = root / ".learning/probes" / probe_id
    if probe_root.exists():
        raise CaseError(f"probe already exists: {probe_id}")
    (probe_root / "scripts").mkdir(parents=True)
    (probe_root / "artifacts").mkdir()
    (probe_root / ".tmp").mkdir()
    (probe_root / "plan.md").write_text("# Probe Plan\n\n## Hypothesis\n\n## Prediction If True\n\n## Prediction If False\n\n## Inputs And Frozen Evidence\n\n## Changed And Controlled Variables\n\n## Evaluation Measure\n\n## Stop Conditions\n", encoding="utf-8")
    (probe_root / "result.md").write_text("# Probe Result\n\nNot executed.\n", encoding="utf-8")
    (probe_root / "manifest.yaml").write_text(
        "\n".join(
            (
                "schema_version: 1.0.0",
                f"probe_id: {json.dumps(probe_id)}",
                f"case_file: {json.dumps(case_path.name)}",
                f"case_sha256: {digest}",
                "status: draft",
                "hypothesis: ''",
                "prediction_if_true: ''",
                "prediction_if_false: ''",
                "changed_variable: ''",
                "controlled_variables: []",
                "inputs: []",
                "writes: []",
                "evaluation_measure: ''",
                "seed: null",
                "workdir: ''",
                "environment: {}",
                "max_wall_seconds: 600",
                "max_gpu_processes: 1",
                "commands: []",
                "artifacts: []",
                "started_at: null",
                "ended_at: null",
                "exit_code: null",
                "",
            )
        ),
        encoding="utf-8",
    )
    return probe_root


def _language(root: Path) -> str | None:
    """Extract dossier language from brief frontmatter without a YAML dependency."""

    brief = root / ".learning/brief.md"
    if not brief.is_file():
        return None
    match = re.search(r'(?m)^language:\s*["\']?([^"\'\n]+)', brief.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else None


def validate(path: str | Path) -> dict[str, object]:
    """Check dossier separation, sealed case identities, state JSON, and links."""

    root = _root(path)
    errors: list[str] = []
    warnings: list[str] = []
    for relative in VISIBLE_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing human-facing file: {relative}")
    for relative in HIDDEN_DIRECTORIES:
        if not (root / relative).is_dir():
            errors.append(f"missing hidden directory: {relative}")
    for relative in (".learning/brief.md", ".learning/evidence-index.yaml", ".learning/decision-tree.md", ".learning/record.md", ".learning/audit/cross-examination.md", ".learning/state/workers.json", ".learning/state/processes.json"):
        if not (root / relative).is_file():
            errors.append(f"missing hidden file: {relative}")
    if not _language(root):
        errors.append("missing language in .learning/brief.md")
    gitignore = root / ".gitignore"
    if not gitignore.is_file() or "*" not in gitignore.read_text(encoding="utf-8").splitlines():
        errors.append("dossier root .gitignore must contain '*'")
    for forbidden in ("decision-tree.md", "record.md", "audit", "probes", "workers.json"):
        if (root / forbidden).exists():
            errors.append(f"agent material remains human-visible: {forbidden}")

    for case_path in _case_files(root):
        errors.extend(_case_errors(case_path))
        sidecar = case_path.with_suffix(case_path.suffix + ".sha256")
        if not sidecar.is_file():
            status = _frontmatter_value(case_path.read_text(encoding="utf-8"), "status")
            if status == "sealed":
                errors.append(f"sealed case lacks SHA-256 sidecar: {case_path.name}")
            else:
                warnings.append(f"unsealed draft case: {case_path.name}")
            continue
        parts = sidecar.read_text(encoding="ascii").split()
        if len(parts) < 2 or parts[1] != case_path.name:
            errors.append(f"invalid case sidecar: {sidecar.name}")
        elif parts[0] != _sha256(case_path):
            errors.append(f"sealed case hash mismatch: {case_path.name}")
        elif _frontmatter_value(case_path.read_text(encoding="utf-8"), "status") != "sealed":
            errors.append(f"sealed case has non-sealed status: {case_path.name}")

    probes_root = root / ".learning/probes"
    if probes_root.is_dir():
        for probe in sorted(path for path in probes_root.iterdir() if path.is_dir()):
            for relative in ("manifest.yaml", "plan.md", "result.md", "scripts", "artifacts", ".tmp"):
                if not (probe / relative).exists():
                    errors.append(f"probe {probe.name} is missing {relative}")
            manifest_path = probe / "manifest.yaml"
            if not manifest_path.is_file():
                continue
            manifest = manifest_path.read_text(encoding="utf-8")
            case_name = _frontmatter_value(manifest, "case_file")
            case_digest = _frontmatter_value(manifest, "case_sha256")
            if case_name is None or not CASE_PATTERN.fullmatch(case_name):
                errors.append(f"probe {probe.name} has invalid case_file")
            else:
                case_path = root / ".learning/cases" / case_name
                try:
                    expected_digest = _sealed_digest(case_path)
                except (CaseError, OSError) as error:
                    errors.append(f"probe {probe.name} case identity failed: {error}")
                else:
                    if case_digest != expected_digest:
                        errors.append(f"probe {probe.name} has mismatched case_sha256")
            if _frontmatter_value(manifest, "max_wall_seconds") != "600":
                errors.append(f"probe {probe.name} must retain max_wall_seconds=600")
            if _frontmatter_value(manifest, "max_gpu_processes") != "1":
                errors.append(f"probe {probe.name} must retain max_gpu_processes=1")
            status = _frontmatter_value(manifest, "status")
            if status not in {"draft", "ready", "running", "completed", "failed", "cancelled"}:
                errors.append(f"probe {probe.name} has invalid status={status!r}")
            if status == "draft":
                warnings.append(f"draft probe: {probe.name}")
            else:
                for field in ("hypothesis", "prediction_if_true", "prediction_if_false", "changed_variable", "evaluation_measure", "workdir"):
                    if _frontmatter_value(manifest, field) in {None, ""}:
                        errors.append(f"probe {probe.name} must define {field} before status={status}")
                for field in ("controlled_variables", "inputs", "writes", "commands"):
                    if _frontmatter_value(manifest, field) in {None, "", "[]"}:
                        errors.append(f"probe {probe.name} must define non-empty {field} before status={status}")
                if _frontmatter_value(manifest, "seed") in {None, "", "null"}:
                    errors.append(f"probe {probe.name} must define seed before status={status}")
                workdir = _frontmatter_value(manifest, "workdir")
                if workdir:
                    workdir_path = Path(workdir).expanduser()
                    if not workdir_path.is_absolute() or not workdir_path.resolve().is_relative_to(probe.resolve()):
                        errors.append(f"probe {probe.name} workdir must remain inside its probe directory")
                if (probe / "plan.md").is_file():
                    sections = _section_bodies((probe / "plan.md").read_text(encoding="utf-8"))
                    for heading in PROBE_REQUIRED_SECTIONS:
                        if not sections.get(heading, ""):
                            errors.append(f"probe {probe.name} has empty plan section: {heading}")
            if status in {"completed", "failed"} and _frontmatter_value(manifest, "exit_code") in {None, "null"}:
                errors.append(f"probe {probe.name} must record exit_code for status={status}")

    for state_name, list_name in (("workers.json", "workers"), ("processes.json", "processes")):
        state_path = root / ".learning/state" / state_name
        if state_path.is_file():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                if not isinstance(state, dict) or not isinstance(state.get(list_name), list):
                    errors.append(f"{state_name} must contain a {list_name} list")
                    continue
                entries = state[list_name]
                required = (
                    ("worker_id", "runtime_handle", "primary_lens", "phase", "case_file", "case_sha256", "lane_path", "status")
                    if list_name == "workers"
                    else ("process_id", "title", "owner", "command", "workdir", "status", "notify_on_exit", "case_file", "case_sha256", "probe_id", "gpu_devices")
                )
                active_owners: set[str] = set()
                runtime_handles: set[str] = set()
                process_ids: set[str] = set()
                for index, entry in enumerate(entries):
                    if not isinstance(entry, dict):
                        errors.append(f"{state_name} entry {index} must be a mapping")
                        continue
                    missing = [field for field in required if field not in entry]
                    if missing:
                        errors.append(f"{state_name} entry {index} is missing fields: {', '.join(missing)}")
                        continue
                    if list_name == "workers":
                        if entry.get("phase") not in {"blind-audit", "cross-examination", "probe"}:
                            errors.append(f"workers.json entry {index} has invalid phase={entry.get('phase')!r}")
                        if entry.get("status") not in {"running", "waiting", "completed", "failed", "cancelled", "probe"}:
                            errors.append(f"workers.json entry {index} has invalid status={entry.get('status')!r}")
                        handle = str(entry["runtime_handle"])
                        if not handle or handle in runtime_handles:
                            errors.append(f"workers.json has invalid or duplicate runtime_handle: {handle}")
                        runtime_handles.add(handle)
                        lane_path = (root / str(entry["lane_path"])).resolve()
                        lanes_root = (root / ".learning/audit/lanes").resolve()
                        if not lane_path.is_relative_to(lanes_root) or lane_path.suffix != ".md":
                            errors.append(f"workers.json entry {index} has lane outside audit/lanes")
                        lane = str(lane_path)
                        if entry.get("status") in {"running", "waiting", "probe"} and lane in active_owners:
                            errors.append(f"workers.json has duplicate active lane owner: {entry['lane_path']}")
                        if entry.get("status") in {"running", "waiting", "probe"}:
                            active_owners.add(lane)
                        case_name = str(entry["case_file"])
                        if not CASE_PATTERN.fullmatch(case_name):
                            errors.append(f"workers.json entry {index} has invalid case_file={case_name!r}")
                        else:
                            case_path = root / ".learning/cases" / case_name
                            try:
                                expected_digest = _sealed_digest(case_path)
                            except (CaseError, OSError) as error:
                                errors.append(f"workers.json entry {index} case identity failed: {error}")
                            else:
                                if entry.get("case_sha256") != expected_digest:
                                    errors.append(f"workers.json entry {index} has mismatched case_sha256")
                    else:
                        if entry.get("status") not in {"running", "exited", "failed", "killed"}:
                            errors.append(f"processes.json entry {index} has invalid status={entry.get('status')!r}")
                        process_id = str(entry["process_id"])
                        if not process_id or process_id in process_ids:
                            errors.append(f"processes.json has invalid or duplicate process_id: {process_id}")
                        process_ids.add(process_id)
                        if not Path(str(entry["workdir"])).expanduser().is_absolute():
                            errors.append(f"processes.json entry {index} workdir must be absolute")
                        case_name = str(entry["case_file"])
                        if not CASE_PATTERN.fullmatch(case_name):
                            errors.append(f"processes.json entry {index} has invalid case_file={case_name!r}")
                        else:
                            case_path = root / ".learning/cases" / case_name
                            try:
                                expected_digest = _sealed_digest(case_path)
                            except (CaseError, OSError) as error:
                                errors.append(f"processes.json entry {index} case identity failed: {error}")
                            else:
                                if entry.get("case_sha256") != expected_digest:
                                    errors.append(f"processes.json entry {index} has mismatched case_sha256")
                if list_name == "workers" and len([entry for entry in entries if isinstance(entry, dict) and entry.get("status") in {"running", "waiting", "probe"}]) > 8:
                    errors.append("workers.json exceeds eight active learning workers")
            except json.JSONDecodeError as error:
                errors.append(f"{state_name} is invalid JSON: {error.msg}")

    for markdown in root.glob("**/*.md"):
        text = markdown.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            if not (markdown.parent / target).resolve().exists():
                errors.append(f"broken link: {markdown.relative_to(root)} -> {raw_target}")
    return {
        "errors": sorted(set(errors)),
        "language": _language(root),
        "ok": not errors,
        "path": str(root),
        "warnings": sorted(set(warnings)),
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the intentionally small dossier-maintenance interface."""

    parser = argparse.ArgumentParser(description="Maintain learning-forensics case dossiers")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a non-destructive dossier skeleton")
    init.add_argument("--path", required=True)
    init.add_argument("--language", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--question")
    new_case_parser = commands.add_parser("new-case", help="create the next numbered blind case draft")
    new_case_parser.add_argument("--path", required=True)
    seal = commands.add_parser("seal-case", help="seal one numbered case with SHA-256")
    seal.add_argument("--path", required=True)
    seal.add_argument("--case", required=True)
    probe = commands.add_parser("new-probe", help="create an isolated probe skeleton")
    probe.add_argument("--path", required=True)
    probe.add_argument("--id", required=True)
    probe.add_argument("--case", required=True)
    check = commands.add_parser("validate", help="validate dossier structure and identities")
    check.add_argument("--path", required=True)
    check.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one deterministic maintenance operation and return shell status."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            result: object = initialize(args.path, language=args.language, title=args.title, question=args.question)
        elif args.command == "new-case":
            result = new_case(args.path)
        elif args.command == "seal-case":
            result = seal_case(args.path, case_name=args.case)
        elif args.command == "new-probe":
            result = new_probe(args.path, probe_id=args.id, case_name=args.case)
        else:
            validation = validate(args.path)
            if args.json:
                sys.stdout.write(json.dumps(validation, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            else:
                sys.stdout.write(("valid" if validation["ok"] else "invalid") + f": {validation['path']}\n")
                for error in validation["errors"]:
                    sys.stdout.write(f"error: {error}\n")
                for warning in validation["warnings"]:
                    sys.stdout.write(f"warning: {warning}\n")
            return 0 if validation["ok"] else 1
        sys.stdout.write(str(result) + "\n")
        return 0
    except (CaseError, OSError, UnicodeError) as error:
        sys.stderr.write(f"error: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
