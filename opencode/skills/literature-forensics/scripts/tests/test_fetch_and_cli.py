from __future__ import annotations

from hashlib import sha256
import json

import httpx
import pytest

from literature_forensics.backends import HttpClient
from literature_forensics.cache import Cache
from literature_forensics import cli
from literature_forensics.cli import main
from literature_forensics.dossier import initialize_dossier
from literature_forensics.fetch import DownloadError, fetch_pdf
from literature_forensics.models import BackendRecord, Work, parse_identifier


def test_fetch_is_contained_size_bounded_and_checksummed(tmp_path):
    dossier = initialize_dossier(tmp_path / "dossier", "Title")
    pdf = b"%PDF-1.7\nmock contents\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"Content-Length": str(len(pdf))}, content=pdf, request=request
        )

    with Cache(dossier / ".state" / "literature-cache.sqlite") as cache:
        work = Work(
            title="../../unsafe",
            doi="10.1000/fetch",
            pdf_url="https://example.test/paper.pdf",
        )
        cache.upsert_record(BackendRecord("crossref", "10.1000/fetch", work, {}))
        client = httpx.Client(transport=httpx.MockTransport(handler))
        result = fetch_pdf(
            dossier,
            cache,
            parse_identifier("10.1000/fetch"),
            HttpClient(client, retries=0),
        )
        target = dossier / result["path"]
        assert target.is_file()
        assert target.resolve().is_relative_to((dossier / "papers").resolve())
        assert result["sha256"] == sha256(pdf).hexdigest()
        assert target.read_bytes() == pdf
        with pytest.raises(DownloadError, match="size cap"):
            fetch_pdf(
                dossier,
                cache,
                parse_identifier("10.1000/fetch"),
                HttpClient(client, retries=0),
                force=True,
                max_bytes=4,
            )
        client.close()


@pytest.mark.parametrize(
    ("body", "content_type", "message"),
    (
        (b"<html>login</html>", "text/html", "unsafe content type"),
        (b"<html>login</html>", "application/pdf", "missing a PDF signature"),
        (b"", "application/pdf", "body is empty"),
    ),
)
def test_fetch_rejects_html_and_empty_bodies(tmp_path, body, content_type, message):
    dossier = initialize_dossier(tmp_path / "dossier", "Title")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"Content-Type": content_type}, content=body, request=request
        )

    with Cache(dossier / ".state" / "literature-cache.sqlite") as cache:
        work = Work(
            title="Unsafe response",
            doi="10.1000/unsafe",
            pdf_url="https://example.test/paper.pdf",
        )
        cache.upsert_record(BackendRecord("crossref", "10.1000/unsafe", work, {}))
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with pytest.raises(DownloadError, match=message):
            fetch_pdf(
                dossier,
                cache,
                parse_identifier("10.1000/unsafe"),
                HttpClient(client, retries=0),
            )
        assert not list((dossier / "papers").glob("*.pdf"))
        client.close()


def test_cli_doctor_compact_json_and_init(tmp_path, capsys, monkeypatch):
    dossier = tmp_path / "dossier"
    assert (
        main(["init", "--dossier", str(dossier), "--title", "CLI Title", "--json"]) == 0
    )
    init_payload = capsys.readouterr().out.strip()
    assert ": " not in init_payload
    assert json.loads(init_payload)["initialized"] is True

    assert main(["doctor", "--dossier", str(dossier), "--json"]) == 0
    doctor_payload = capsys.readouterr().out.strip()
    assert ": " not in doctor_payload
    assert json.loads(doctor_payload)["dossier"]["initialized"] is True
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    monkeypatch.delenv("CROSSREF_MAILTO", raising=False)
    assert main(["doctor", "--dossier", str(dossier)]) == 0
    assert "Credentials present: none" in capsys.readouterr().out


def test_cli_partial_backend_errors_preserve_output_without_failure(
    tmp_path, capsys, monkeypatch
):
    dossier = initialize_dossier(tmp_path / "dossier", "Title")
    record = BackendRecord(
        "crossref", "10.1000/partial", Work(title="Usable", doi="10.1000/partial"), {}
    )

    class PartialManager:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def search(self, *_):
            return [record], ["arxiv: HTTP 503 from test"]

    monkeypatch.setattr(cli, "BackendManager", PartialManager)
    assert (
        main(
            [
                "search",
                "query",
                "--sources",
                "arxiv,crossref",
                "--dossier",
                str(dossier),
                "--json",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["results"][0]["title"] == "Usable"
    assert "arxiv: HTTP 503" in captured.err

    class FailedManager(PartialManager):
        def search(self, *_):
            return [], ["arxiv: HTTP 503 from test"]

    monkeypatch.setattr(cli, "BackendManager", FailedManager)
    assert (
        main(
            [
                "search",
                "query",
                "--sources",
                "arxiv",
                "--dossier",
                str(dossier),
                "--json",
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["results"] == []
    assert "arxiv: HTTP 503" in captured.err


def test_cli_empty_graph_with_remote_error_fails(tmp_path, capsys, monkeypatch):
    dossier = initialize_dossier(tmp_path / "dossier", "Title")

    class FailedGraphManager:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def graph(self, *_):
            return [], ["semantic-scholar: HTTP 503 from test"]

    monkeypatch.setattr(cli, "BackendManager", FailedGraphManager)
    status = main(["graph", "arXiv:2401.12345", "--dossier", str(dossier), "--json"])
    captured = capsys.readouterr()
    assert status == 1
    assert json.loads(captured.out)["edges"] == []
    assert "semantic-scholar: HTTP 503" in captured.err
