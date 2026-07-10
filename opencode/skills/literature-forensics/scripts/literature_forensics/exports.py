"""Deterministic exports from only dossier-local cached evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from .cache import Cache
from .models import Work


class ExportError(ValueError):
    """Raised when an export destination is unsafe or unsuitable."""


def _escape_bibtex(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def bibtex_export(works: list[Work]) -> str:
    """Produce small, conservative BibTeX that is stable across invocations."""
    entries: list[str] = []
    for work in sorted(works, key=lambda item: item.citekey):
        fields: list[tuple[str, str]] = []
        if work.authors:
            fields.append(("author", " and ".join(work.authors)))
        fields.append(("title", work.title))
        if work.venue:
            fields.append(("journal", work.venue))
        if work.year:
            fields.append(("year", str(work.year)))
        if work.doi:
            fields.append(("doi", work.doi))
        if work.arxiv_id:
            fields.extend((("eprint", work.arxiv_id), ("archivePrefix", "arXiv")))
        if work.url:
            fields.append(("url", work.url))
        kind = "article" if work.venue else "misc"
        lines = [f"@{kind}{{{work.citekey},"]
        lines.extend(
            f"  {name} = {{{_escape_bibtex(value)}}}," for name, value in fields
        )
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries) + ("\n" if entries else "")


def search_log_export(cache: Cache) -> str:
    lines = [
        "# Cached Search Log",
        "",
        "| Date | Query | Sources | Abstracts | Results |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for row in cache.search_log_rows():
        query = str(row["query_text"]).replace("|", r"\|")
        sources = str(row["sources"]).replace("|", r"\|")
        abstracts = "yes" if row["include_abstracts"] else "no"
        lines.append(
            f"| {row['created_at']} | {query} | {sources} | {abstracts} | {row['result_count']} |"
        )
    return "\n".join(lines) + "\n"


def citation_graph_export(cache: Cache) -> str:
    payload = {"edges": [edge.to_dict() for edge in cache.list_edges()]}
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    )


def export_content(cache: Cache, kind: str) -> str:
    if kind == "bibtex":
        return bibtex_export(cache.list_works())
    if kind == "search-log":
        return search_log_export(cache)
    if kind == "citation-graph":
        return citation_graph_export(cache)
    raise ExportError(f"unknown export kind: {kind}")


def write_export(content: str, output: str | Path) -> Path:
    raw = str(output)
    if not raw or "\x00" in raw:
        raise ExportError("output path is invalid")
    path = Path(raw).expanduser().resolve()
    if path.exists() and path.is_dir():
        raise ExportError("output path is a directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, path)
    return path
