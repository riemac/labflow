from __future__ import annotations

import httpx
import pytest

from literature_forensics.backends import (
    BackendManager,
    HttpClient,
    SemanticScholarBackend,
)
from literature_forensics.models import parse_identifier


def _paper(paper_id: str, title: str) -> dict[str, object]:
    return {
        "paperId": paper_id,
        "title": title,
        "authors": [{"name": "Author"}],
        "year": 2024,
    }


def test_semantic_scholar_direction_and_depth_rejection():
    origin = "12345678-abcd"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"].startswith("literature-forensics/")
        if request.url.path.endswith("/references"):
            return httpx.Response(
                200, json={"data": [{"citedPaper": _paper("aaaaaaaa-bbbb", "Cited")}]}
            )
        if request.url.path.endswith("/citations"):
            return httpx.Response(
                200, json={"data": [{"citingPaper": _paper("cccccccc-dddd", "Citing")}]}
            )
        return httpx.Response(200, json=_paper(origin, "Origin"))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    http = HttpClient(client, retries=0)
    backend = SemanticScholarBackend(http)
    identifier = parse_identifier(f"s2:{origin}")

    references = backend.graph(identifier, "references", 10)
    citations = backend.graph(identifier, "citations", 10)
    assert references[0].citing.title == "Origin"
    assert references[0].cited.title == "Cited"
    assert citations[0].citing.title == "Citing"
    assert citations[0].cited.title == "Origin"

    manager = BackendManager(http)
    with pytest.raises(ValueError, match="depth 1"):
        manager.graph(identifier, "both", 2, 10)
    client.close()


def test_missing_credentials_and_unavailable_backend_are_graceful(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_MAILTO", raising=False)
    assert BackendManager.credentials() == {
        "crossref_mailto": False,
        "openalex_api_key": False,
        "semantic_scholar_api_key": False,
    }

    def unavailable(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"message": "down"})

    client = httpx.Client(transport=httpx.MockTransport(unavailable))
    manager = BackendManager(HttpClient(client, retries=0, sleep=lambda _: None))
    records, errors = manager.search("query", ["crossref"], 1, False)
    assert records == []
    assert errors and errors[0].startswith("crossref: HTTP 503")
    client.close()
