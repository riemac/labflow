#!/usr/bin/env python3
"""Create, migrate, and validate human-first literature research directories.

This standard-library helper owns only deterministic filesystem mechanics. It
does not search papers, interpret evidence, write research conclusions, or
manage OpenCode task sessions. Scholarly retrieval belongs to Litnav; research
judgment belongs to the coordinator and literature worker.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Sequence


VISIBLE_FILES = ("README.md", "overview.md", "MAP.md", "topics/README.md")
HIDDEN_DIRECTORIES = (
    ".research/audit/papers",
    ".research/audit/lanes",
    ".research/library",
    ".research/state",
)
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


class ResearchError(ValueError):
    """Reject destructive migrations, invalid paths, and malformed dossiers."""


@dataclass(frozen=True)
class Action:
    """Describe one deterministic migration operation for dry-run review."""

    kind: str
    source: str | None
    destination: str


def _today() -> str:
    """Return the UTC date used in stable research frontmatter."""

    return datetime.now(UTC).date().isoformat()


def _root(value: str | Path) -> Path:
    """Resolve a non-empty research path without requiring it to exist."""

    raw = str(value)
    if not raw or "\x00" in raw:
        raise ResearchError("research path is invalid")
    return Path(raw).expanduser().resolve()


def _frontmatter(
    *, language: str, title: str, kind: str, question: str | None = None
) -> str:
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
    """Return minimal human and audit entry files without synthesizing findings."""

    chinese = language.lower().startswith("zh")
    question_text = question or (
        "在开始检索前明确研究问题。"
        if chinese
        else "State the research question before retrieval."
    )
    if chinese:
        return {
            "README.md": "# 文献调研\n\n- [研究概览](overview.md)\n- [研究地图](MAP.md)\n- [主题报告](topics/)\n",
            "overview.md": f"{_frontmatter(language=language, title=title, kind='research-overview', question=question)}\n\n# 研究概览\n\n## 研究问题\n\n{question_text}\n\n## 当前回答\n\n尚未综合。\n",
            "MAP.md": f"{_frontmatter(language=language, title=title, kind='research-map', question=question)}\n\n# 研究地图\n\n尚未策展。\n",
            "topics/README.md": "# 主题报告\n\n每个文件是一篇面向研究者的完整主题调研报告。\n",
            ".research/brief.md": f"{_frontmatter(language=language, title=title, kind='research-brief', question=question)}\n\n# Research Brief\n\n## Question\n\n{question_text}\n",
            ".gitignore": ".research/state/\n.research/library/*.pdf\n",
        }
    return {
        "README.md": "# Literature Research\n\n- [Overview](overview.md)\n- [Research map](MAP.md)\n- [Topic reports](topics/)\n",
        "overview.md": f"{_frontmatter(language=language, title=title, kind='research-overview', question=question)}\n\n# Research Overview\n\n## Question\n\n{question_text}\n\n## Current Answer\n\nNot synthesized yet.\n",
        "MAP.md": f"{_frontmatter(language=language, title=title, kind='research-map', question=question)}\n\n# Research Map\n\nNot curated yet.\n",
        "topics/README.md": "# Topic Reports\n\nEach file is a complete, researcher-facing topic report.\n",
        ".research/brief.md": f"{_frontmatter(language=language, title=title, kind='research-brief', question=question)}\n\n# Research Brief\n\n## Question\n\n{question_text}\n",
        ".gitignore": ".research/state/\n.research/library/*.pdf\n",
    }


def initialize(
    path: str | Path, *, language: str, title: str, question: str | None
) -> Path:
    """Create a non-destructive human/audit dossier skeleton."""

    root = _root(path)
    files = _skeleton(language=language, title=title, question=question)
    conflicts = [relative for relative in files if (root / relative).exists()]
    if conflicts:
        raise ResearchError(
            "refusing to overwrite existing files: " + ", ".join(conflicts)
        )
    root.mkdir(parents=True, exist_ok=True)
    for relative in HIDDEN_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return root


def _migration_actions(root: Path) -> list[Action]:
    """Plan a v1-to-v2 migration without reading or rewriting research claims."""

    actions: list[Action] = []
    direct_moves = {
        "brief.md": ".research/audit/legacy-brief.md",
        "search-log.md": ".research/search-log.md",
        "bibliography.bib": ".research/bibliography.bib",
        "README.md": ".research/audit/legacy-overview.md",
        "MAP.md": ".research/audit/legacy-MAP.md",
    }
    for source, destination in direct_moves.items():
        if (root / source).exists():
            actions.append(Action("move", source, destination))
    for source_directory, pattern, destination_directory in (
        ("papers", "*.md", ".research/audit/papers"),
        ("papers", "*.pdf", ".research/library"),
        ("topics", "*.md", ".research/audit/lanes"),
    ):
        directory = root / source_directory
        if not directory.is_dir():
            continue
        for source in sorted(directory.glob(pattern)):
            actions.append(
                Action(
                    "move",
                    source.relative_to(root).as_posix(),
                    f"{destination_directory}/{source.name}",
                )
            )
    state = root / ".state"
    if state.is_dir():
        for source in sorted(path for path in state.rglob("*") if path.is_file()):
            relative = source.relative_to(state).as_posix()
            actions.append(
                Action(
                    "move",
                    source.relative_to(root).as_posix(),
                    f".research/state/{relative}",
                )
            )
    for relative in (*VISIBLE_FILES, ".research/brief.md"):
        actions.append(Action("create", None, relative))
    return actions


def _rewrite_audit_card(path: Path) -> None:
    """Point migrated paper-card PDF locators at the hidden research library."""

    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'(?m)^(\s*pdf:\s*["\']?)([^"\'\n/]+\.pdf)(["\']?\s*)$',
        r"\1../../library/\2\3",
        text,
    )
    text = re.sub(r"\]\(([^/)]+\.pdf)\)", r"](../../library/\1)", text)
    path.write_text(text, encoding="utf-8")


def migrate_v1(
    path: str | Path,
    *,
    language: str,
    title: str,
    question: str | None,
    apply: bool,
) -> list[Action]:
    """Plan or apply an idempotent v1 dossier migration."""

    root = _root(path)
    if not root.is_dir():
        raise ResearchError(f"research directory does not exist: {root}")
    actions = _migration_actions(root)
    if not apply:
        return actions

    skeleton = _skeleton(language=language, title=title, question=question)
    for relative in HIDDEN_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for action in actions:
        destination = root / action.destination
        if action.kind == "move":
            source = root / str(action.source)
            if not source.exists():
                continue
            if destination.exists():
                raise ResearchError(
                    f"migration destination already exists: {destination}"
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            if destination.parent.name == "papers" and destination.suffix == ".md":
                _rewrite_audit_card(destination)
        elif not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(skeleton[action.destination], encoding="utf-8")

    for relative in ("papers", "topics", ".state"):
        directory = root / relative
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    gitignore = root / ".gitignore"
    required = [".research/state/", ".research/library/*.pdf"]
    existing = (
        gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    )
    gitignore.write_text(
        "\n".join(dict.fromkeys([*existing, *required])) + "\n", encoding="utf-8"
    )
    return actions


def _language(path: Path) -> str | None:
    """Extract the dossier language from brief frontmatter without a YAML dependency."""

    brief = path / ".research/brief.md"
    if not brief.is_file():
        return None
    match = re.search(
        r'(?m)^language:\s*["\']?([^"\'\n]+)', brief.read_text(encoding="utf-8")
    )
    return match.group(1).strip() if match else None


def validate(path: str | Path) -> dict[str, object]:
    """Check structural separation and relative Markdown links without judging content."""

    root = _root(path)
    errors: list[str] = []
    warnings: list[str] = []
    for relative in VISIBLE_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing human-facing file: {relative}")
    if not _language(root):
        errors.append("missing language in .research/brief.md")
    for forbidden in (
        "papers",
        "brief.md",
        "search-log.md",
        "bibliography.bib",
        ".state",
    ):
        if (root / forbidden).exists():
            errors.append(f"agent material remains visible: {forbidden}")
    visible_pdfs = [
        path.relative_to(root).as_posix()
        for path in root.glob("**/*.pdf")
        if ".research" not in path.parts
    ]
    errors.extend(f"PDF remains visible: {relative}" for relative in visible_pdfs)

    for markdown in root.glob("**/*.md"):
        text = markdown.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (markdown.parent / target).resolve()
            if not resolved.exists():
                errors.append(
                    f"broken link: {markdown.relative_to(root)} -> {raw_target}"
                )
    audit_cards = list((root / ".research/audit/papers").glob("*.md"))
    library_pdfs = list((root / ".research/library").glob("*.pdf"))
    if audit_cards and not library_pdfs:
        warnings.append("audit cards exist but the local PDF library is empty")
    return {
        "errors": sorted(set(errors)),
        "language": _language(root),
        "ok": not errors,
        "path": str(root),
        "warnings": sorted(set(warnings)),
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the intentionally small internal research-maintenance interface."""

    parser = argparse.ArgumentParser(
        description="Maintain literature-forensics research directories"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="create a non-destructive v2 skeleton")
    init.add_argument("--path", required=True)
    init.add_argument("--language", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--question")
    migrate = commands.add_parser(
        "migrate-v1", help="plan or apply a v1-to-v2 migration"
    )
    migrate.add_argument("--path", required=True)
    migrate.add_argument("--language", required=True)
    migrate.add_argument("--title", required=True)
    migrate.add_argument("--question")
    migrate.add_argument("--apply", action="store_true")
    check = commands.add_parser(
        "validate", help="validate structure and relative links"
    )
    check.add_argument("--path", required=True)
    check.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute one deterministic directory operation and return a shell status."""

    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            root = initialize(
                args.path,
                language=args.language,
                title=args.title,
                question=args.question,
            )
            sys.stdout.write(str(root) + "\n")
            return 0
        if args.command == "migrate-v1":
            actions = migrate_v1(
                args.path,
                language=args.language,
                title=args.title,
                question=args.question,
                apply=args.apply,
            )
            sys.stdout.write(
                json.dumps(
                    [asdict(action) for action in actions], ensure_ascii=False, indent=2
                )
                + "\n"
            )
            return 0
        result = validate(args.path)
        if args.json:
            sys.stdout.write(
                json.dumps(
                    result, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                + "\n"
            )
        else:
            sys.stdout.write(
                ("valid" if result["ok"] else "invalid") + f": {result['path']}\n"
            )
            for error in result["errors"]:
                sys.stdout.write(f"error: {error}\n")
            for warning in result["warnings"]:
                sys.stdout.write(f"warning: {warning}\n")
        return 0 if result["ok"] else 1
    except (ResearchError, OSError, KeyError) as error:
        sys.stderr.write(f"error: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
