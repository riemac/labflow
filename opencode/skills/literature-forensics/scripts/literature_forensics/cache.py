"""Dossier-local SQLite cache with transactional identity reconciliation."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import sqlite3
import time
from typing import Iterator, Sequence, cast

from .models import BackendRecord, CitationEdge, Identifier, Work


SCHEMA_VERSION = 2
_LOCK_RETRIES = 8

_SCHEMA_V1 = (
    """
    CREATE TABLE IF NOT EXISTS works (
        id INTEGER PRIMARY KEY,
        canonical_key TEXT NOT NULL UNIQUE,
        doi TEXT UNIQUE,
        arxiv_id TEXT UNIQUE,
        openalex_id TEXT UNIQUE,
        s2_id TEXT UNIQUE,
        title TEXT NOT NULL,
        title_norm TEXT NOT NULL,
        authors_json TEXT NOT NULL,
        year INTEGER,
        abstract TEXT,
        venue TEXT,
        url TEXT,
        pdf_url TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS works_title_year_idx ON works(title_norm, year)",
    """
    CREATE TABLE IF NOT EXISTS source_records (
        id INTEGER PRIMARY KEY,
        work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        source_id TEXT NOT NULL,
        raw_json TEXT NOT NULL,
        retrieved_at TEXT NOT NULL,
        UNIQUE(source, source_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS source_records_work_idx ON source_records(work_id)",
    """
    CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY,
        query_text TEXT NOT NULL,
        sources TEXT NOT NULL,
        include_abstracts INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS query_results (
        query_id INTEGER NOT NULL REFERENCES queries(id) ON DELETE CASCADE,
        work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        rank INTEGER NOT NULL,
        PRIMARY KEY(query_id, work_id, source)
    )
    """,
    "CREATE INDEX IF NOT EXISTS query_results_work_idx ON query_results(work_id)",
    """
    CREATE TABLE IF NOT EXISTS citation_edges (
        id INTEGER PRIMARY KEY,
        citing_work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
        cited_work_id INTEGER NOT NULL REFERENCES works(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        retrieved_at TEXT NOT NULL,
        CHECK(citing_work_id != cited_work_id),
        UNIQUE(citing_work_id, cited_work_id, source)
    )
    """,
    "CREATE INDEX IF NOT EXISTS citation_edges_citing_idx ON citation_edges(citing_work_id)",
    "CREATE INDEX IF NOT EXISTS citation_edges_cited_idx ON citation_edges(cited_work_id)",
    """
    CREATE TABLE IF NOT EXISTS downloads (
        work_id INTEGER PRIMARY KEY REFERENCES works(id) ON DELETE CASCADE,
        url TEXT NOT NULL,
        relative_path TEXT NOT NULL UNIQUE,
        sha256 TEXT NOT NULL,
        bytes INTEGER NOT NULL,
        downloaded_at TEXT NOT NULL
    )
    """,
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class Cache:
    """A small SQLite repository. One instance owns one connection."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._pragma("PRAGMA journal_mode=WAL")
        self._pragma("PRAGMA foreign_keys=ON")
        self._pragma("PRAGMA busy_timeout=5000")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Cache":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _pragma(self, statement: str) -> None:
        for attempt in range(_LOCK_RETRIES):
            try:
                self.conn.execute(statement)
                return
            except sqlite3.OperationalError as error:
                if "locked" not in str(error).lower() or attempt == _LOCK_RETRIES - 1:
                    raise
                time.sleep(0.02 * (2**attempt))

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Acquire the writer lock before reads so identity bridges cannot race."""
        for attempt in range(_LOCK_RETRIES):
            try:
                self.conn.execute("BEGIN IMMEDIATE")
                break
            except sqlite3.OperationalError as error:
                if "locked" not in str(error).lower() or attempt == _LOCK_RETRIES - 1:
                    raise
                time.sleep(0.02 * (2**attempt))
        try:
            yield self.conn
        except BaseException:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()

    def _migrate(self) -> None:
        with self.transaction() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
            )
            row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
            version = int(row[0]) if row and row[0] is not None else 0
            if version > SCHEMA_VERSION:
                raise RuntimeError(f"cache schema {version} is newer than this tool")
            if version < 1:
                for statement in _SCHEMA_V1:
                    conn.execute(statement)
                conn.execute("INSERT INTO schema_version(version) VALUES (1)")
                version = 1
            if version < 2:
                # Version 2 formalizes transaction-safe bridge merges; no DDL is needed.
                conn.execute("INSERT INTO schema_version(version) VALUES (2)")

    @staticmethod
    def _work_from_row(row: sqlite3.Row) -> Work:
        return Work(
            title=row["title"],
            authors=tuple(json.loads(row["authors_json"])),
            year=row["year"],
            doi=row["doi"],
            arxiv_id=row["arxiv_id"],
            openalex_id=row["openalex_id"],
            s2_id=row["s2_id"],
            abstract=row["abstract"],
            venue=row["venue"],
            url=row["url"],
            pdf_url=row["pdf_url"],
        )

    def _find_matches(self, work: Work) -> list[sqlite3.Row]:
        """Return every directly bridged row, ordered by identity precedence."""
        matches: dict[int, tuple[int, sqlite3.Row]] = {}
        for precedence, (column, value) in enumerate(
            (
                ("doi", work.doi),
                ("arxiv_id", work.arxiv_id),
                ("openalex_id", work.openalex_id),
                ("s2_id", work.s2_id),
            )
        ):
            if not value:
                continue
            for row in self.conn.execute(
                f"SELECT * FROM works WHERE {column} = ?", (value,)
            ).fetchall():
                work_id = int(row["id"])
                matches[work_id] = min(
                    matches.get(work_id, (precedence, row)),
                    (precedence, row),
                    key=lambda item: item[0],
                )
        if matches:
            return [
                item[1]
                for item in sorted(
                    matches.values(), key=lambda item: (item[0], int(item[1]["id"]))
                )
            ]
        if not work.title_norm:
            return []
        candidates = self.conn.execute(
            "SELECT * FROM works WHERE title_norm = ? ORDER BY id", (work.title_norm,)
        ).fetchall()
        return [row for row in candidates if self._title_fallback_compatible(row, work)]

    @staticmethod
    def _title_fallback_compatible(row: sqlite3.Row, incoming: Work) -> bool:
        """Conservatively join a preprint and venue version lacking shared IDs.

        Exact normalized titles are not sufficient by themselves: annual reports,
        benchmark editions, and reused generic titles can collide. Same-year rows
        retain the original fallback. Adjacent-year rows additionally require an
        overlapping author surname, which covers typical arXiv-to-proceedings lag
        without merging unrelated works merely because their titles match.
        """
        if any(
            left and right and left != right
            for left, right in (
                (row["doi"], incoming.doi),
                (row["arxiv_id"], incoming.arxiv_id),
                (row["openalex_id"], incoming.openalex_id),
                (row["s2_id"], incoming.s2_id),
            )
        ):
            return False
        existing = Cache._work_from_row(row)
        if existing.year == incoming.year:
            return True
        if (
            existing.year is not None
            and incoming.year is not None
            and abs(existing.year - incoming.year) > 1
        ):
            return False
        existing_surnames = {
            author.casefold().split()[-1]
            for author in existing.authors
            if author.split()
        }
        incoming_surnames = {
            author.casefold().split()[-1]
            for author in incoming.authors
            if author.split()
        }
        return bool(existing_surnames.intersection(incoming_surnames))

    @staticmethod
    def _merge_works(rows: Sequence[sqlite3.Row], incoming: Work) -> Work:
        works = [Cache._work_from_row(row) for row in rows] + [incoming]

        def first(name: str) -> object:
            return next(
                (
                    getattr(work, name)
                    for work in works
                    if getattr(work, name) is not None and getattr(work, name) != ()
                ),
                None,
            )

        # A DOI-bearing venue record describes the formal publication, while an
        # arXiv record often carries a better abstract, complete author names,
        # and the accessible PDF. Merge fields by those evidence roles instead
        # of taking every scalar from whichever backend happened to arrive first.
        publication = max(
            works,
            key=lambda work: (
                int(bool(work.doi and work.venue)),
                int(bool(work.doi)),
                int(bool(work.venue)),
                int(bool(work.openalex_id)),
            ),
        )
        author_source = max(
            works,
            key=lambda work: (
                len(work.authors),
                sum(len(author) for author in work.authors),
            ),
        )
        abstract_source = max(works, key=lambda work: len(work.abstract or ""))

        return Work(
            title=publication.title,
            authors=author_source.authors,
            year=publication.year or cast(int | None, first("year")),
            doi=cast(str | None, first("doi")),
            arxiv_id=cast(str | None, first("arxiv_id")),
            openalex_id=cast(str | None, first("openalex_id")),
            s2_id=cast(str | None, first("s2_id")),
            abstract=abstract_source.abstract,
            venue=publication.venue or cast(str | None, first("venue")),
            url=publication.url or cast(str | None, first("url")),
            pdf_url=cast(str | None, first("pdf_url")),
        )

    def _repoint_work(self, primary_id: int, donor_id: int) -> None:
        """Move all dependent rows before deleting a bridged duplicate work."""
        self.conn.execute(
            "UPDATE source_records SET work_id = ? WHERE work_id = ?",
            (primary_id, donor_id),
        )

        query_rows = self.conn.execute(
            "SELECT query_id, source, rank FROM query_results WHERE work_id = ?",
            (donor_id,),
        ).fetchall()
        for row in query_rows:
            self.conn.execute(
                """
                INSERT INTO query_results(query_id, work_id, source, rank) VALUES (?, ?, ?, ?)
                ON CONFLICT(query_id, work_id, source) DO UPDATE SET rank = MIN(query_results.rank, excluded.rank)
                """,
                (row["query_id"], primary_id, row["source"], row["rank"]),
            )
        self.conn.execute("DELETE FROM query_results WHERE work_id = ?", (donor_id,))

        edge_rows = self.conn.execute(
            "SELECT id, citing_work_id, cited_work_id, source, retrieved_at FROM citation_edges WHERE citing_work_id = ? OR cited_work_id = ?",
            (donor_id, donor_id),
        ).fetchall()
        for edge in edge_rows:
            citing_id = (
                primary_id
                if edge["citing_work_id"] == donor_id
                else edge["citing_work_id"]
            )
            cited_id = (
                primary_id
                if edge["cited_work_id"] == donor_id
                else edge["cited_work_id"]
            )
            self.conn.execute("DELETE FROM citation_edges WHERE id = ?", (edge["id"],))
            if citing_id != cited_id:
                self.conn.execute(
                    """
                    INSERT INTO citation_edges(citing_work_id, cited_work_id, source, retrieved_at) VALUES (?, ?, ?, ?)
                    ON CONFLICT(citing_work_id, cited_work_id, source) DO UPDATE SET
                        retrieved_at = MAX(citation_edges.retrieved_at, excluded.retrieved_at)
                    """,
                    (citing_id, cited_id, edge["source"], edge["retrieved_at"]),
                )

        primary_download = self.conn.execute(
            "SELECT 1 FROM downloads WHERE work_id = ?", (primary_id,)
        ).fetchone()
        if primary_download:
            self.conn.execute("DELETE FROM downloads WHERE work_id = ?", (donor_id,))
        else:
            self.conn.execute(
                "UPDATE downloads SET work_id = ? WHERE work_id = ?",
                (primary_id, donor_id),
            )
        self.conn.execute("DELETE FROM works WHERE id = ?", (donor_id,))

    def upsert_record(self, record: BackendRecord) -> int:
        """Upsert a work and atomically merge every row bridged by its identifiers."""
        if not record.source or not record.source_id:
            raise ValueError("source records require non-empty source and source_id")
        with self.transaction() as conn:
            matches = self._find_matches(record.work)
            now = utc_now()
            if not matches:
                values = self._work_values(record.work, now)
                cursor = conn.execute(
                    """
                    INSERT INTO works(
                        canonical_key, doi, arxiv_id, openalex_id, s2_id, title, title_norm,
                        authors_json, year, abstract, venue, url, pdf_url, created_at, updated_at
                    ) VALUES (
                        :canonical_key, :doi, :arxiv_id, :openalex_id, :s2_id, :title, :title_norm,
                        :authors_json, :year, :abstract, :venue, :url, :pdf_url, :created_at, :updated_at
                    )
                    """,
                    values,
                )
                if cursor.lastrowid is None:
                    raise RuntimeError("SQLite did not return a work row ID")
                work_id = int(cursor.lastrowid)
            else:
                primary = matches[0]
                work_id = int(primary["id"])
                merged = self._merge_works(matches, record.work)
                for donor in matches[1:]:
                    self._repoint_work(work_id, int(donor["id"]))
                conn.execute(
                    """
                    UPDATE works SET canonical_key=:canonical_key, doi=:doi, arxiv_id=:arxiv_id,
                        openalex_id=:openalex_id, s2_id=:s2_id, title=:title, title_norm=:title_norm,
                        authors_json=:authors_json, year=:year, abstract=:abstract, venue=:venue,
                        url=:url, pdf_url=:pdf_url, updated_at=:updated_at
                    WHERE id=:id
                    """,
                    {**self._work_values(merged, now), "id": work_id},
                )
            conn.execute(
                """
                INSERT INTO source_records(work_id, source, source_id, raw_json, retrieved_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, source_id) DO UPDATE SET
                    work_id=excluded.work_id, raw_json=excluded.raw_json, retrieved_at=excluded.retrieved_at
                """,
                (
                    work_id,
                    record.source,
                    record.source_id,
                    json.dumps(
                        record.raw,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    now,
                ),
            )
        return work_id

    @staticmethod
    def _work_values(work: Work, now: str) -> dict[str, object]:
        return {
            "canonical_key": work.identity,
            "doi": work.doi,
            "arxiv_id": work.arxiv_id,
            "openalex_id": work.openalex_id,
            "s2_id": work.s2_id,
            "title": work.title,
            "title_norm": work.title_norm,
            "authors_json": json.dumps(
                list(work.authors), ensure_ascii=False, separators=(",", ":")
            ),
            "year": work.year,
            "abstract": work.abstract,
            "venue": work.venue,
            "url": work.url,
            "pdf_url": work.pdf_url,
            "created_at": now,
            "updated_at": now,
        }

    def get_work(self, identifier: Identifier) -> tuple[int, Work] | None:
        if identifier.kind == "doi":
            column, value = "doi", identifier.value
        elif identifier.kind == "arxiv":
            column, value = "arxiv_id", identifier.value
        elif identifier.kind == "openalex":
            column, value = "openalex_id", identifier.value
        elif identifier.kind in {"s2", "corpus"}:
            column, value = "s2_id", identifier.value
        else:
            return None
        row = self.conn.execute(
            f"SELECT * FROM works WHERE {column} = ?", (value,)
        ).fetchone()
        return (int(row["id"]), self._work_from_row(row)) if row else None

    def work_for_id(self, work_id: int) -> Work:
        row = self.conn.execute(
            "SELECT * FROM works WHERE id = ?", (work_id,)
        ).fetchone()
        if row is None:
            raise KeyError(work_id)
        return self._work_from_row(row)

    def record_query(
        self,
        query: str,
        sources: Sequence[str],
        include_abstracts: bool,
        ranked_records: Sequence[tuple[str, int, int]],
    ) -> int:
        with self.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO queries(query_text, sources, include_abstracts, created_at) VALUES (?, ?, ?, ?)",
                (query, ",".join(sources), int(include_abstracts), utc_now()),
            )
            if cursor.lastrowid is None:
                raise RuntimeError("SQLite did not return a query row ID")
            query_id = int(cursor.lastrowid)
            conn.executemany(
                """
                INSERT INTO query_results(query_id, work_id, source, rank) VALUES (?, ?, ?, ?)
                ON CONFLICT(query_id, work_id, source) DO UPDATE SET rank=excluded.rank
                """,
                [
                    (query_id, work_id, source, rank)
                    for source, rank, work_id in ranked_records
                ],
            )
        return query_id

    def upsert_edge(self, edge: CitationEdge) -> tuple[int, int]:
        citing_id = self.upsert_record(
            BackendRecord(edge.source, edge.citing.identity, edge.citing, {})
        )
        cited_id = self.upsert_record(
            BackendRecord(edge.source, edge.cited.identity, edge.cited, {})
        )
        with self.transaction() as conn:
            if citing_id != cited_id:
                conn.execute(
                    """
                    INSERT INTO citation_edges(citing_work_id, cited_work_id, source, retrieved_at) VALUES (?, ?, ?, ?)
                    ON CONFLICT(citing_work_id, cited_work_id, source) DO UPDATE SET retrieved_at=excluded.retrieved_at
                    """,
                    (citing_id, cited_id, edge.source, utc_now()),
                )
        return citing_id, cited_id

    def list_works(self) -> list[Work]:
        rows = self.conn.execute(
            "SELECT * FROM works ORDER BY canonical_key, id"
        ).fetchall()
        return sorted(
            (self._work_from_row(row) for row in rows),
            key=lambda work: (work.citekey, work.identity),
        )

    def list_edges(self) -> list[CitationEdge]:
        rows = self.conn.execute(
            """
            SELECT edge.source, citing.id AS citing_id, cited.id AS cited_id
            FROM citation_edges AS edge
            JOIN works AS citing ON citing.id = edge.citing_work_id
            JOIN works AS cited ON cited.id = edge.cited_work_id
            ORDER BY edge.source, citing.canonical_key, cited.canonical_key
            """
        ).fetchall()
        return [
            CitationEdge(
                self.work_for_id(row["citing_id"]),
                self.work_for_id(row["cited_id"]),
                row["source"],
            )
            for row in rows
        ]

    def record_download(
        self, work_id: int, url: str, relative_path: str, digest: str, size: int
    ) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO downloads(work_id, url, relative_path, sha256, bytes, downloaded_at) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(work_id) DO UPDATE SET url=excluded.url, relative_path=excluded.relative_path,
                    sha256=excluded.sha256, bytes=excluded.bytes, downloaded_at=excluded.downloaded_at
                """,
                (work_id, url, relative_path, digest, size, utc_now()),
            )

    def stats(self) -> dict[str, int]:
        tables = (
            "works",
            "source_records",
            "queries",
            "query_results",
            "citation_edges",
            "downloads",
        )
        result = {
            table: int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }
        result["wal_enabled"] = int(
            self.conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        )
        return result

    def prune(self, days: int = 180) -> dict[str, int]:
        if not 1 <= days <= 3650:
            raise ValueError("prune days must be between 1 and 3650")
        cutoff = (
            (datetime.now(UTC) - timedelta(days=days))
            .replace(microsecond=0)
            .isoformat()
        )
        with self.transaction() as conn:
            deleted_queries = conn.execute(
                "DELETE FROM queries WHERE created_at < ?", (cutoff,)
            ).rowcount
        return {"deleted_queries": deleted_queries, "older_than_days": days}

    def search_log_rows(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            """
            SELECT query_text, sources, include_abstracts, created_at, COUNT(query_results.work_id) AS result_count
            FROM queries LEFT JOIN query_results ON queries.id = query_results.query_id
            GROUP BY queries.id ORDER BY queries.created_at, queries.id
            """
        ).fetchall()
