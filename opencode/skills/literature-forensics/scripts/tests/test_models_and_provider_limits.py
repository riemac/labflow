from __future__ import annotations

import httpx

from literature_forensics.backends import (
    BackendManager,
    CrossrefBackend,
    HttpClient,
    OpenAlexBackend,
    SemanticScholarBackend,
)
from literature_forensics.models import normalize_arxiv, normalize_doi, parse_identifier


def _openalex_work(index: int) -> dict[str, object]:
    return {
        "id": f"https://openalex.org/W{index}",
        "title": f"OpenAlex {index}",
        "publication_year": 2024,
    }


def _paper(index: int) -> dict[str, object]:
    return {
        "paperId": f"00000000-0000-0000-0000-{index:012d}",
        "title": f"Semantic {index}",
        "year": 2024,
    }


def test_arxiv_versions_and_crossref_doi_special_characters():
    assert normalize_arxiv("https://arxiv.org/abs/2401.12345v7") == "2401.12345"
    assert parse_identifier("arXiv:2401.12345v2").value == "2401.12345"
    special = "10.1002/(SICI)1099-0844(199912)17:4<290::AID-BMC522>3.0.CO;2-3."
    assert normalize_doi(special) == special.lower()
    assert normalize_doi("10.1000/has space") is None
    assert normalize_doi("10.1000/../escape") is None
    assert normalize_doi("10.1000/control\x00") is None


def test_provider_caps_and_manager_global_search_budget():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        host = request.url.host
        if host == "api.openalex.org":
            count = int(request.url.params.get("per-page", "1"))
            return httpx.Response(
                200, json={"results": [_openalex_work(index) for index in range(count)]}
            )
        if host == "api.semanticscholar.org":
            count = int(request.url.params.get("limit", "1"))
            return httpx.Response(
                200, json={"data": [_paper(index) for index in range(count)]}
            )
        return httpx.Response(200, json={"message": {"items": []}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    http = HttpClient(client, retries=0)
    manager = BackendManager(http)
    records, errors = manager.search(
        "query", ["openalex", "semantic-scholar", "crossref"], 250, False
    )
    assert errors == []
    assert len(records) == 167
    assert [request.url.host for request in requests] == [
        "api.openalex.org",
        "api.semanticscholar.org",
        "api.crossref.org",
    ]
    assert requests[0].url.params["per-page"] == "84"
    assert requests[1].url.params["limit"] == "83"
    assert requests[2].url.params["rows"] == "83"

    OpenAlexBackend(http).search("query", 999, False)
    SemanticScholarBackend(http).search("query", 999, False)
    CrossrefBackend(http).search("query", 9_999, False)
    assert requests[-3].url.params["per-page"] == "200"
    assert requests[-2].url.params["limit"] == "100"
    assert requests[-1].url.params["rows"] == "1000"
    client.close()


def test_graph_budgets_and_openalex_reference_batching():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/works/W1"):
            return httpx.Response(
                200,
                json={
                    **_openalex_work(1),
                    "referenced_works": [
                        "https://openalex.org/W2",
                        "https://openalex.org/W3",
                    ],
                },
            )
        if request.url.params.get("filter", "").startswith("openalex_id:"):
            return httpx.Response(
                200, json={"results": [_openalex_work(2), _openalex_work(3)]}
            )
        return httpx.Response(200, json={"results": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = OpenAlexBackend(HttpClient(client, retries=0))
    edges = backend.graph(parse_identifier("openalex:W1"), "references", 5)
    assert len(edges) == 2
    assert len(requests) == 2
    assert requests[1].url.params["filter"] == "openalex_id:W2|W3"
    assert "select" in requests[1].url.params
    client.close()
