from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading

from literature_forensics.cache import Cache
from literature_forensics.exports import (
    bibtex_export,
    citation_graph_export,
    search_log_export,
)
from literature_forensics.models import (
    BackendRecord,
    CitationEdge,
    Work,
    parse_identifier,
)


def _record(source: str, source_id: str, work: Work) -> BackendRecord:
    return BackendRecord(source, source_id, work, {"source_id": source_id})


def test_normalized_dedupe_precedence_and_wal(tmp_path):
    with Cache(tmp_path / "cache.sqlite") as cache:
        first = Work(
            title="A Test: Of Metadata",
            authors=("Ada Lovelace",),
            year=2024,
            doi="10.1000/ABC",
        )
        second = Work(
            title="A Test Of Metadata",
            authors=("Ada Lovelace",),
            year=2024,
            doi="doi:10.1000/abc",
            arxiv_id="2401.12345",
        )
        first_id = cache.upsert_record(_record("crossref", "10.1000/abc", first))
        second_id = cache.upsert_record(_record("arxiv", "2401.12345", second))

        assert first_id == second_id
        assert cache.stats()["works"] == 1
        assert cache.stats()["source_records"] == 2
        assert cache.conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert cache.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_deterministic_bibtex_search_log_and_graph_export(tmp_path):
    with Cache(tmp_path / "cache.sqlite") as cache:
        origin = Work(
            title="Origin & Evidence",
            authors=("Ada Lovelace",),
            year=2024,
            doi="10.1000/origin",
            venue="Journal",
        )
        cited = Work(
            title="Prior Work",
            authors=("Grace Hopper",),
            year=2023,
            arxiv_id="2301.12345",
        )
        origin_id = cache.upsert_record(_record("crossref", "10.1000/origin", origin))
        cited_id = cache.upsert_record(_record("arxiv", "2301.12345", cited))
        cache.record_query("evidence", ["arxiv"], False, [("arxiv", 1, cited_id)])
        cache.upsert_edge(
            CitationEdge(
                cache.work_for_id(origin_id),
                cache.work_for_id(cited_id),
                "semantic-scholar",
            )
        )

        bibliography = bibtex_export(cache.list_works())
        assert bibliography == bibtex_export(cache.list_works())
        assert "Origin \\& Evidence" in bibliography
        assert citation_graph_export(cache) == citation_graph_export(cache)
        assert '"edges":[' in citation_graph_export(cache)
        assert "| evidence | arxiv | no | 1 |" in search_log_export(cache)


def test_bridge_merge_repoints_all_dependents_and_canonicalizes(tmp_path):
    with Cache(tmp_path / "cache.sqlite") as cache:
        doi_work = Work(title="DOI record", year=2024, doi="10.1000/bridge")
        arxiv_work = Work(title="arXiv record", year=2024, arxiv_id="2401.12345v2")
        doi_id = cache.upsert_record(_record("crossref", "10.1000/bridge", doi_work))
        arxiv_id = cache.upsert_record(_record("arxiv", "2401.12345", arxiv_work))
        target_id = cache.upsert_record(
            _record(
                "crossref", "10.1000/target", Work(title="Target", doi="10.1000/target")
            )
        )
        cache.record_query(
            "bridge",
            ["crossref", "arxiv"],
            False,
            [("crossref", 2, doi_id), ("arxiv", 1, arxiv_id)],
        )
        cache.upsert_edge(
            CitationEdge(
                cache.work_for_id(arxiv_id),
                cache.work_for_id(target_id),
                "semantic-scholar",
            )
        )
        cache.record_download(
            arxiv_id, "https://example.test/paper.pdf", "papers/arxiv.pdf", "a" * 64, 10
        )

        merged_id = cache.upsert_record(
            _record(
                "semantic-scholar",
                "bridge-s2",
                Work(
                    title="Combined",
                    year=2024,
                    doi="10.1000/bridge",
                    arxiv_id="2401.12345",
                ),
            )
        )

        assert merged_id == doi_id
        assert cache.get_work(parse_identifier("10.1000/bridge"))[0] == doi_id
        assert cache.get_work(parse_identifier("arXiv:2401.12345v7"))[0] == doi_id
        assert cache.conn.execute("SELECT COUNT(*) FROM works").fetchone()[0] == 2
        source_ids = cache.conn.execute(
            "SELECT DISTINCT work_id FROM source_records WHERE (source = 'crossref' AND source_id = '10.1000/bridge') OR (source = 'arxiv' AND source_id = '2401.12345')"
        ).fetchall()
        query_ids = cache.conn.execute(
            "SELECT DISTINCT work_id FROM query_results"
        ).fetchall()
        assert [row[0] for row in source_ids] == [doi_id]
        assert [row[0] for row in query_ids] == [doi_id]
        assert (
            cache.conn.execute("SELECT citing_work_id FROM citation_edges").fetchone()[
                0
            ]
            == doi_id
        )
        assert (
            cache.conn.execute("SELECT work_id FROM downloads").fetchone()[0] == doi_id
        )
        assert (
            cache.conn.execute(
                "SELECT canonical_key FROM works WHERE id = ?", (doi_id,)
            ).fetchone()[0]
            == "doi:10.1000/bridge"
        )
        assert cache.list_works()[0].identity == "doi:10.1000/bridge"


def test_concurrent_cache_initialization_and_upserts(tmp_path):
    path = tmp_path / "concurrent.sqlite"
    barrier = threading.Barrier(6)

    def write(index: int) -> int:
        barrier.wait()
        with Cache(path) as cache:
            return cache.upsert_record(
                _record(
                    "crossref",
                    f"10.1000/{index}",
                    Work(title=f"Work {index}", doi=f"10.1000/{index}"),
                )
            )

    with ThreadPoolExecutor(max_workers=6) as executor:
        ids = list(executor.map(write, range(6)))
    with Cache(path) as cache:
        assert len(set(ids)) == 6
        assert cache.stats()["works"] == 6


def test_preprint_and_venue_version_merge_by_exact_title_author_and_adjacent_year(
    tmp_path,
):
    with Cache(tmp_path / "cache.sqlite") as cache:
        preprint = Work(
            title="GET-Zero: Graph Embodiment Transformer for Zero-shot Embodiment Generalization",
            authors=("Austin Patel", "Shuran Song"),
            year=2024,
            arxiv_id="2407.15002",
        )
        venue = Work(
            title="GET-Zero: Graph Embodiment Transformer for Zero-Shot Embodiment Generalization",
            authors=("A.B. Patel", "Shuran Song"),
            year=2025,
            doi="10.1109/icra55743.2025.11127922",
            venue="ICRA",
        )
        preprint_id = cache.upsert_record(_record("arxiv", "2407.15002", preprint))
        venue_id = cache.upsert_record(_record("openalex", "W4413917693", venue))

        assert preprint_id == venue_id
        assert cache.stats()["works"] == 1
        merged = cache.work_for_id(preprint_id)
        assert merged.arxiv_id == "2407.15002"
        assert merged.doi == "10.1109/icra55743.2025.11127922"
        assert merged.year == 2025
        assert merged.venue == "ICRA"


def test_adjacent_year_title_match_without_shared_author_stays_separate(tmp_path):
    with Cache(tmp_path / "cache.sqlite") as cache:
        first_id = cache.upsert_record(
            _record(
                "source-a",
                "a",
                Work(title="Annual Benchmark", authors=("Alice One",), year=2024),
            )
        )
        second_id = cache.upsert_record(
            _record(
                "source-b",
                "b",
                Work(title="Annual Benchmark", authors=("Bob Two",), year=2025),
            )
        )

        assert first_id != second_id
        assert cache.stats()["works"] == 2
