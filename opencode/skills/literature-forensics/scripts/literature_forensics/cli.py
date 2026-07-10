"""Command-line interface for a dossier-local literature evidence workflow."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from typing import Any, Sequence

from .backends import BackendError, BackendManager, HttpClient, SUPPORTED_SOURCES
from .cache import Cache
from .dossier import (
    DossierError,
    archive_worker,
    cache_path,
    initialize_dossier,
    list_workers,
    resolve_dossier,
    set_worker,
)
from .exports import ExportError, export_content, write_export
from .fetch import DownloadError, fetch_pdf
from .models import ValidationError, clean_text, parse_identifier


def _add_json_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit stable compact JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="literature-forensics",
        description="Local-first literature metadata and evidence helper",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create a human-first dossier skeleton")
    init.add_argument("--dossier", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--question")
    init.add_argument("--force", action="store_true")
    _add_json_option(init)

    search = commands.add_parser("search", help="search and cache normalized works")
    search.add_argument("query")
    search.add_argument("--sources", default=",".join(SUPPORTED_SOURCES))
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--include-abstracts", action="store_true")
    search.add_argument("--dossier", required=True)
    _add_json_option(search)

    resolve = commands.add_parser(
        "resolve", help="retrieve canonical metadata for an identifier"
    )
    resolve.add_argument("identifier")
    resolve.add_argument("--dossier", required=True)
    _add_json_option(resolve)

    graph = commands.add_parser("graph", help="retrieve one-hop citation relationships")
    graph.add_argument("identifier")
    graph.add_argument(
        "--direction", choices=("references", "citations", "both"), default="both"
    )
    graph.add_argument("--depth", type=int, default=1)
    graph.add_argument("--limit", type=int, default=20)
    graph.add_argument("--dossier", required=True)
    _add_json_option(graph)

    fetch = commands.add_parser("fetch", help="explicitly download one cached PDF")
    fetch.add_argument("identifier")
    fetch.add_argument("--dossier", required=True)
    fetch.add_argument("--force", action="store_true")
    _add_json_option(fetch)

    export = commands.add_parser("export", help="export cached evidence")
    export.add_argument(
        "--kind", choices=("bibtex", "search-log", "citation-graph"), required=True
    )
    export.add_argument("--dossier", required=True)
    export.add_argument("--output")
    _add_json_option(export)

    worker = commands.add_parser(
        "worker", help="manage the main-agent-owned worker registry"
    )
    worker_commands = worker.add_subparsers(dest="worker_command", required=True)
    worker_set = worker_commands.add_parser(
        "set", help="create or update a worker lane"
    )
    worker_set.add_argument("--dossier", required=True)
    worker_set.add_argument("--lane", required=True)
    worker_set.add_argument("--task-id", required=True)
    worker_set.add_argument("--phase", required=True)
    worker_set.add_argument("--artifact")
    _add_json_option(worker_set)
    worker_list = worker_commands.add_parser("list", help="list worker lanes")
    worker_list.add_argument("--dossier", required=True)
    _add_json_option(worker_list)
    worker_archive = worker_commands.add_parser("archive", help="archive a worker lane")
    worker_archive.add_argument("--dossier", required=True)
    worker_archive.add_argument("--task-id", required=True)
    _add_json_option(worker_archive)

    cache = commands.add_parser("cache", help="inspect or prune cached state")
    cache_commands = cache.add_subparsers(dest="cache_command", required=True)
    cache_stats = cache_commands.add_parser("stats", help="show cache counts")
    cache_stats.add_argument("--dossier", required=True)
    _add_json_option(cache_stats)
    cache_prune = cache_commands.add_parser("prune", help="remove old query history")
    cache_prune.add_argument("--dossier", required=True)
    cache_prune.add_argument("--days", type=int, default=180)
    _add_json_option(cache_prune)

    doctor = commands.add_parser(
        "doctor", help="report local prerequisites and credential presence"
    )
    doctor.add_argument("--dossier", required=True)
    _add_json_option(doctor)
    return parser


def _validate_limit(value: int) -> int:
    if not 1 <= value <= 2_000:
        raise ValueError("--limit must be between 1 and 2000")
    return value


def _parse_sources(value: str) -> list[str]:
    sources = [source.strip() for source in value.split(",") if source.strip()]
    if not sources:
        raise ValueError("--sources must name at least one backend")
    unknown = sorted(set(sources).difference(SUPPORTED_SOURCES))
    if unknown:
        raise ValueError(f"unsupported source(s): {', '.join(unknown)}")
    return list(dict.fromkeys(sources))


def _human_work(work: dict[str, Any]) -> str:
    identifiers = ", ".join(
        value
        for value in (
            work.get("doi"),
            work.get("arxiv_id"),
            work.get("openalex_id"),
            work.get("s2_id"),
        )
        if value
    )
    year = work.get("year") or "n.d."
    return f"{work['title']} ({year})" + (f" [{identifiers}]" if identifiers else "")


def _emit(payload: Any, human: str, as_json: bool) -> None:
    if as_json:
        sys.stdout.write(
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            + "\n"
        )
    else:
        sys.stdout.write(human.rstrip() + "\n")


def _report_remote_errors(errors: list[str]) -> None:
    for error in errors:
        sys.stderr.write(f"error: {error}\n")


def _search(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    query = clean_text(args.query, limit=2_000)
    if not query:
        raise ValueError("query must not be empty")
    sources = _parse_sources(args.sources)
    limit = _validate_limit(args.limit)
    dossier = resolve_dossier(args.dossier)
    with BackendManager() as manager, Cache(cache_path(dossier)) as cache:
        records, errors = manager.search(query, sources, limit, args.include_abstracts)
        work_ids: list[int] = []
        ranks: list[tuple[str, int, int]] = []
        for rank, record in enumerate(records, start=1):
            work_id = cache.upsert_record(record)
            ranks.append((record.source, rank, work_id))
            if work_id not in work_ids:
                work_ids.append(work_id)
        query_id = cache.record_query(query, sources, args.include_abstracts, ranks)
        works = sorted(
            (cache.work_for_id(work_id) for work_id in work_ids),
            key=lambda item: item.citekey,
        )
    payload = {
        "errors": errors,
        "query": query,
        "query_id": query_id,
        "results": [
            work.to_dict(include_abstract=args.include_abstracts) for work in works
        ],
        "sources": sources,
    }
    human = (
        "\n".join(_human_work(work.to_dict(include_abstract=False)) for work in works)
        or "No results."
    )
    return payload, human, errors


def _resolve(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    identifier = parse_identifier(args.identifier)
    dossier = resolve_dossier(args.dossier)
    with BackendManager() as manager, Cache(cache_path(dossier)) as cache:
        records, errors = manager.resolve(identifier)
        work_ids = [cache.upsert_record(record) for record in records]
        cached = cache.get_work(identifier)
        if cached is None and work_ids:
            work = cache.work_for_id(work_ids[0])
        elif cached is not None:
            work = cached[1]
        else:
            raise ValueError(f"no backend returned metadata for {identifier.value}")
    payload = {"errors": errors, "identifier": identifier.value, "work": work.to_dict()}
    return payload, _human_work(work.to_dict(include_abstract=False)), errors


def _graph(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    identifier = parse_identifier(args.identifier)
    limit = _validate_limit(args.limit)
    if args.depth != 1:
        raise ValueError("only --depth 1 is supported in v1")
    dossier = resolve_dossier(args.dossier)
    with BackendManager() as manager, Cache(cache_path(dossier)) as cache:
        edges, errors = manager.graph(identifier, args.direction, args.depth, limit)
        for edge in edges:
            cache.upsert_edge(edge)
    exported = sorted(
        (edge.to_dict() for edge in edges),
        key=lambda item: (item["source"], item["citing"], item["cited"]),
    )
    payload = {
        "depth": 1,
        "direction": args.direction,
        "edges": exported,
        "errors": errors,
        "identifier": identifier.value,
    }
    human = (
        "\n".join(
            f"{edge['citing']} -> {edge['cited']} ({edge['source']})"
            for edge in exported
        )
        or "No edges."
    )
    return payload, human, errors


def _fetch(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    identifier = parse_identifier(args.identifier)
    dossier = resolve_dossier(args.dossier)
    with Cache(cache_path(dossier)) as cache, HttpClient() as http:
        payload = fetch_pdf(dossier, cache, identifier, http, force=args.force)
    return payload, f"Downloaded {payload['path']} ({payload['bytes']} bytes)", []


def _export(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    dossier = resolve_dossier(args.dossier)
    with Cache(cache_path(dossier)) as cache:
        content = export_content(cache, args.kind)
    if args.output:
        output = write_export(content, args.output)
        payload = {"kind": args.kind, "output": str(output)}
        return payload, f"Wrote {args.kind} to {output}", []
    return {"content": content, "kind": args.kind}, content, []


def _worker(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    dossier = resolve_dossier(args.dossier)
    if args.worker_command == "set":
        worker = set_worker(
            dossier,
            lane=args.lane,
            task_id=args.task_id,
            phase=args.phase,
            artifact=args.artifact,
        )
        return worker, f"Updated worker {worker['task_id']} ({worker['phase']})", []
    if args.worker_command == "archive":
        worker = archive_worker(dossier, task_id=args.task_id)
        return worker, f"Archived worker {worker['task_id']}", []
    workers = list_workers(dossier)
    return (
        {"workers": workers},
        "\n".join(
            f"{item['lane']}: {item['task_id']} ({item['phase']})" for item in workers
        )
        or "No workers.",
        [],
    )


def _cache(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    dossier = resolve_dossier(args.dossier)
    with Cache(cache_path(dossier)) as cache:
        payload = (
            cache.stats() if args.cache_command == "stats" else cache.prune(args.days)
        )
    human = "\n".join(f"{key}: {value}" for key, value in sorted(payload.items()))
    return payload, human, []


def _doctor(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    dossier = resolve_dossier(args.dossier, require=False)
    state = dossier / ".state"
    payload = {
        "backends": BackendManager.credentials(),
        "dossier": {
            "exists": dossier.is_dir(),
            "initialized": state.is_dir(),
            "path": str(dossier),
        },
        "python": {
            "implementation": sys.implementation.name,
            "version": ".".join(map(str, sys.version_info[:3])),
        },
        "sqlite": {"version": sqlite3.sqlite_version},
    }
    human = "\n".join(
        (
            f"Python: {payload['python']['version']} ({payload['python']['implementation']})",
            f"SQLite: {payload['sqlite']['version']}",
            f"Dossier initialized: {'yes' if payload['dossier']['initialized'] else 'no'}",
            "Credentials present: "
            + (
                ", ".join(key for key, value in payload["backends"].items() if value)
                or "none"
            ),
        )
    )
    return payload, human, []


def _dispatch(args: argparse.Namespace) -> tuple[dict[str, Any], str, list[str]]:
    if args.command == "init":
        dossier = initialize_dossier(
            args.dossier, args.title, args.question, force=args.force
        )
        payload = {"dossier": str(dossier), "initialized": True}
        return payload, f"Initialized dossier: {dossier}", []
    if args.command == "search":
        return _search(args)
    if args.command == "resolve":
        return _resolve(args)
    if args.command == "graph":
        return _graph(args)
    if args.command == "fetch":
        return _fetch(args)
    if args.command == "export":
        return _export(args)
    if args.command == "worker":
        return _worker(args)
    if args.command == "cache":
        return _cache(args)
    if args.command == "doctor":
        return _doctor(args)
    raise AssertionError(f"unknown command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    """Run a command and return a shell-compatible status code."""
    args = build_parser().parse_args(argv)
    try:
        payload, human, remote_errors = _dispatch(args)
        _emit(payload, human, args.json)
        if remote_errors:
            _report_remote_errors(remote_errors)
            if args.command == "search":
                return int(
                    not payload["results"]
                    and len(remote_errors) == len(payload["sources"])
                )
            if args.command == "graph":
                return int(not payload["edges"] and bool(remote_errors))
        return 0
    except (
        BackendError,
        DossierError,
        DownloadError,
        ExportError,
        ValidationError,
        ValueError,
        OSError,
        sqlite3.Error,
    ) as error:
        sys.stderr.write(f"error: {error}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
