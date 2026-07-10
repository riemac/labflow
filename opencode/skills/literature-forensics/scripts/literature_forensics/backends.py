"""Documented HTTP API adapters for supported scholarly metadata providers."""

from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
import time
from typing import Any, Iterator, Mapping, Sequence, cast
from urllib.parse import quote
import xml.etree.ElementTree as ET

import httpx

from .models import (
    BackendRecord,
    CitationEdge,
    Identifier,
    Work,
    clean_text,
    normalize_arxiv,
    normalize_openalex,
)


USER_AGENT = "literature-forensics/0.1 (+https://github.com/labflow/labflow)"
SUPPORTED_SOURCES = ("arxiv", "openalex", "semantic-scholar", "crossref")


def _direction_budgets(direction: str, limit: int) -> tuple[int, int]:
    """Split a one-hop edge budget across requested directions."""
    if direction == "references":
        return limit, 0
    if direction == "citations":
        return 0, limit
    return (limit + 1) // 2, limit // 2


class BackendError(RuntimeError):
    """A bounded, user-safe error from a remote backend."""


class HttpClient:
    """Synchronous HTTP helper with bounded retries for transient API failures."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        *,
        timeout: float = 15.0,
        retries: int = 2,
        sleep: Any = time.sleep,
    ) -> None:
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(timeout), follow_redirects=True
        )
        self._owns_client = client is None
        self.timeout = timeout
        self.retries = retries
        self.sleep = sleep
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, application/atom+xml;q=0.9",
        }

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _pause(self, response: httpx.Response | None, attempt: int) -> None:
        retry_after = response.headers.get("Retry-After") if response else None
        try:
            delay = (
                min(float(retry_after), 30.0)
                if retry_after
                else min(0.5 * (2**attempt), 8.0)
            )
        except ValueError:
            delay = min(0.5 * (2**attempt), 8.0)
        self.sleep(delay)

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        extra_headers = kwargs.pop("headers", None)
        headers = {
            **self.headers,
            **(extra_headers if isinstance(extra_headers, dict) else {}),
        }
        for attempt in range(self.retries + 1):
            try:
                response = self.client.request(
                    method, url, headers=headers, timeout=self.timeout, **kwargs
                )
            except httpx.RequestError as error:
                if attempt == self.retries:
                    raise BackendError(
                        f"request failed for {url}: {error.__class__.__name__}"
                    ) from error
                self._pause(None, attempt)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.retries:
                    self._pause(response, attempt)
                    continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise BackendError(f"HTTP {response.status_code} from {url}") from error
            return response
        raise AssertionError("unreachable retry loop")

    @contextmanager
    def stream(self, method: str, url: str, **kwargs: Any) -> Iterator[httpx.Response]:
        """Yield one successful streaming response, retrying before any bytes are read."""
        extra_headers = kwargs.pop("headers", None)
        headers = {
            **self.headers,
            **(extra_headers if isinstance(extra_headers, dict) else {}),
        }
        for attempt in range(self.retries + 1):
            try:
                with self.client.stream(
                    method, url, headers=headers, timeout=self.timeout, **kwargs
                ) as response:
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt < self.retries:
                            self._pause(response, attempt)
                            continue
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as error:
                        raise BackendError(
                            f"HTTP {response.status_code} from {url}"
                        ) from error
                    yield response
                    return
            except httpx.RequestError as error:
                if attempt == self.retries:
                    raise BackendError(
                        f"request failed for {url}: {error.__class__.__name__}"
                    ) from error
                self._pause(None, attempt)
        raise AssertionError("unreachable retry loop")


def _json(response: httpx.Response, source: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except json.JSONDecodeError as error:
        raise BackendError(f"{source} returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise BackendError(f"{source} returned an unexpected JSON payload")
    return payload


def _year(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value[:4].isdigit():
        return int(value[:4])
    return None


def _name_list(items: object, *, field: str = "name") -> tuple[str, ...]:
    if not isinstance(items, list):
        return ()
    names: list[str] = []
    for item in items:
        if isinstance(item, dict):
            value = item.get(field)
            if isinstance(value, str) and clean_text(value, limit=300):
                names.append(clean_text(value, limit=300))
    return tuple(names)


class ArxivBackend:
    name = "arxiv"
    endpoint = "https://export.arxiv.org/api/query"
    _atom = "{http://www.w3.org/2005/Atom}"
    _arxiv = "{http://arxiv.org/schemas/atom}"

    def __init__(self, http: HttpClient) -> None:
        self.http = http

    def search(
        self, query: str, limit: int, include_abstracts: bool
    ) -> list[BackendRecord]:
        response = self.http.request(
            "GET",
            self.endpoint,
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": min(limit, 2_000),
            },
        )
        return self._records(response.text, include_abstracts)

    def resolve(self, identifier: Identifier) -> list[BackendRecord]:
        if identifier.kind != "arxiv":
            return []
        response = self.http.request(
            "GET", self.endpoint, params={"id_list": identifier.value, "max_results": 1}
        )
        return self._records(response.text, True)

    def _records(self, xml: str, include_abstracts: bool) -> list[BackendRecord]:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as error:
            raise BackendError("arXiv returned invalid Atom XML") from error
        records: list[BackendRecord] = []
        for entry in root.findall(f"{self._atom}entry"):
            source_url = entry.findtext(f"{self._atom}id", default="")
            arxiv_id = normalize_arxiv(source_url)
            title = entry.findtext(f"{self._atom}title", default="")
            if not arxiv_id or not clean_text(title):
                continue
            pdf_url = None
            doi = entry.findtext(f"{self._arxiv}doi")
            for link in entry.findall(f"{self._atom}link"):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href")
                    break
            authors = tuple(
                clean_text(author.findtext(f"{self._atom}name", default=""), limit=300)
                for author in entry.findall(f"{self._atom}author")
            )
            work = Work(
                title=title,
                authors=tuple(author for author in authors if author),
                year=_year(entry.findtext(f"{self._atom}published", default="")),
                doi=doi,
                arxiv_id=arxiv_id,
                abstract=entry.findtext(f"{self._atom}summary")
                if include_abstracts
                else None,
                url=source_url.replace("http://", "https://", 1),
                pdf_url=pdf_url.replace("http://", "https://", 1)
                if isinstance(pdf_url, str)
                else None,
            )
            raw = {"id": source_url, "title": title, "arxiv_id": arxiv_id}
            records.append(BackendRecord(self.name, arxiv_id, work, raw))
        return records


class OpenAlexBackend:
    name = "openalex"
    endpoint = "https://api.openalex.org"
    _search_cap = 200
    _graph_select = "id,title,authorships,publication_year,doi,primary_location,best_oa_location,referenced_works"

    def __init__(self, http: HttpClient, api_key: str | None = None) -> None:
        self.http = http
        self.api_key = api_key or os.getenv("OPENALEX_API_KEY")

    def _params(self, params: Mapping[str, object]) -> dict[str, object]:
        if self.api_key:
            return {**params, "api_key": self.api_key}
        return dict(params)

    def search(
        self, query: str, limit: int, include_abstracts: bool
    ) -> list[BackendRecord]:
        payload = _json(
            self.http.request(
                "GET",
                f"{self.endpoint}/works",
                params=self._params(
                    {"search": query, "per-page": min(limit, self._search_cap)}
                ),
            ),
            self.name,
        )
        return self._records(payload.get("results"), include_abstracts)

    def resolve(self, identifier: Identifier) -> list[BackendRecord]:
        return self._resolve(identifier)

    def _resolve(
        self, identifier: Identifier, *, graph: bool = False
    ) -> list[BackendRecord]:
        select = {"select": self._graph_select} if graph else {}
        if identifier.kind == "openalex":
            payload = _json(
                self.http.request(
                    "GET",
                    f"{self.endpoint}/works/{quote(identifier.value, safe='')}",
                    params=self._params(select),
                ),
                self.name,
            )
            return self._records([payload], True)
        if identifier.kind == "doi":
            payload = _json(
                self.http.request(
                    "GET",
                    f"{self.endpoint}/works",
                    params=self._params(
                        {
                            "filter": f"doi:https://doi.org/{identifier.value}",
                            "per-page": 1,
                            **select,
                        }
                    ),
                ),
                self.name,
            )
            return self._records(payload.get("results"), True)
        return []

    def graph(
        self, identifier: Identifier, direction: str, limit: int
    ) -> list[CitationEdge]:
        origins = self._resolve(identifier, graph=True)
        if not origins:
            return []
        origin = origins[0]
        origin_id = origin.work.openalex_id
        if not origin_id:
            return []
        edges: list[CitationEdge] = []
        reference_limit, citation_limit = _direction_budgets(
            direction, min(limit, self._search_cap)
        )
        if reference_limit:
            raw_references = origin.raw.get("referenced_works", [])
            if not isinstance(raw_references, list):
                raw_references = []
            reference_ids = [
                normalize_openalex(reference) for reference in raw_references
            ]
            reference_ids = [
                reference_id for reference_id in reference_ids if reference_id
            ][:reference_limit]
            for start in range(0, len(reference_ids), self._search_cap):
                batch = reference_ids[start : start + self._search_cap]
                payload = _json(
                    self.http.request(
                        "GET",
                        f"{self.endpoint}/works",
                        params=self._params(
                            {
                                "filter": "openalex_id:" + "|".join(batch),
                                "per-page": len(batch),
                                "select": self._graph_select,
                            }
                        ),
                    ),
                    self.name,
                )
                for record in self._records(payload.get("results"), True):
                    edges.append(CitationEdge(origin.work, record.work, self.name))
        if citation_limit:
            payload = _json(
                self.http.request(
                    "GET",
                    f"{self.endpoint}/works",
                    params=self._params(
                        {
                            "filter": f"cites:{origin_id}",
                            "per-page": citation_limit,
                            "select": self._graph_select,
                        }
                    ),
                ),
                self.name,
            )
            for record in self._records(payload.get("results"), True):
                edges.append(CitationEdge(record.work, origin.work, self.name))
        return edges[:limit]

    def _records(self, payload: object, include_abstracts: bool) -> list[BackendRecord]:
        if not isinstance(payload, list):
            return []
        records: list[BackendRecord] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            record = self._record(item, include_abstracts)
            if record:
                records.append(record)
        return records

    def _record(
        self, item: dict[str, Any], include_abstracts: bool
    ) -> BackendRecord | None:
        openalex_id = normalize_openalex(item.get("id"))
        title = clean_text(item.get("title"), limit=2_000)
        if not openalex_id or not title:
            return None
        authorships = item.get("authorships")
        authors: list[str] = []
        if isinstance(authorships, list):
            for entry in authorships:
                author = entry.get("author") if isinstance(entry, dict) else None
                name = author.get("display_name") if isinstance(author, dict) else None
                if isinstance(name, str) and clean_text(name, limit=300):
                    authors.append(clean_text(name, limit=300))
        locations = item.get("best_oa_location") or item.get("primary_location") or {}
        if not isinstance(locations, dict):
            locations = {}
        inverted = item.get("abstract_inverted_index")
        abstract = _openalex_abstract(inverted) if include_abstracts else None
        work = Work(
            title=title,
            authors=tuple(authors),
            year=_year(item.get("publication_year")),
            doi=item.get("doi"),
            openalex_id=openalex_id,
            abstract=abstract,
            venue=_openalex_venue(item),
            url=locations.get("landing_page_url") or item.get("doi"),
            pdf_url=locations.get("pdf_url"),
        )
        return BackendRecord(self.name, openalex_id, work, item)


def _openalex_abstract(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    words: dict[int, str] = {}
    for token, positions in value.items():
        if not isinstance(token, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int) and 0 <= position < 20_000:
                words[position] = token
    return " ".join(words[index] for index in sorted(words)) or None


def _openalex_venue(item: dict[str, Any]) -> str | None:
    location = item.get("primary_location")
    source = location.get("source") if isinstance(location, dict) else None
    name = source.get("display_name") if isinstance(source, dict) else None
    return name if isinstance(name, str) else None


class SemanticScholarBackend:
    name = "semantic-scholar"
    endpoint = "https://api.semanticscholar.org/graph/v1"
    _fields = "paperId,title,authors,year,abstract,venue,externalIds,url,openAccessPdf"
    _graph_fields = "paperId,title,authors,year,externalIds"
    _search_cap = 100
    _graph_cap = 1_000

    def __init__(self, http: HttpClient, api_key: str | None = None) -> None:
        self.http = http
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key} if self.api_key else {}

    def _request(self, path: str, params: dict[str, object]) -> dict[str, Any]:
        response = self.http.request(
            "GET", f"{self.endpoint}{path}", params=params, headers=self._headers()
        )
        return _json(response, self.name)

    def search(
        self, query: str, limit: int, include_abstracts: bool
    ) -> list[BackendRecord]:
        payload = self._request(
            "/paper/search",
            {
                "query": query,
                "limit": min(limit, self._search_cap),
                "fields": self._fields,
            },
        )
        return self._records(payload.get("data"), include_abstracts)

    def resolve(self, identifier: Identifier) -> list[BackendRecord]:
        return self._resolve(identifier, self._fields)

    def _resolve(self, identifier: Identifier, fields: str) -> list[BackendRecord]:
        if identifier.kind == "openalex":
            return []
        payload = self._request(
            f"/paper/{quote(identifier.api_value, safe=':')}", {"fields": fields}
        )
        return self._records([payload], True)

    def graph(
        self, identifier: Identifier, direction: str, limit: int
    ) -> list[CitationEdge]:
        if identifier.kind == "openalex":
            return []
        origins = self._resolve(identifier, self._graph_fields)
        if not origins:
            return []
        origin = origins[0]
        paper = quote(identifier.api_value, safe=":")
        edges: list[CitationEdge] = []
        reference_limit, citation_limit = _direction_budgets(
            direction, min(limit, self._graph_cap)
        )
        if reference_limit:
            payload = self._request(
                f"/paper/{paper}/references",
                {
                    "limit": reference_limit,
                    "fields": "citedPaper."
                    + self._graph_fields.replace(",", ",citedPaper."),
                },
            )
            for item in payload.get("data", []):
                record = self._record(
                    item.get("citedPaper") if isinstance(item, dict) else None, True
                )
                if record:
                    edges.append(CitationEdge(origin.work, record.work, self.name))
        if citation_limit:
            payload = self._request(
                f"/paper/{paper}/citations",
                {
                    "limit": citation_limit,
                    "fields": "citingPaper."
                    + self._graph_fields.replace(",", ",citingPaper."),
                },
            )
            for item in payload.get("data", []):
                record = self._record(
                    item.get("citingPaper") if isinstance(item, dict) else None, True
                )
                if record:
                    edges.append(CitationEdge(record.work, origin.work, self.name))
        return edges[:limit]

    def _records(self, payload: object, include_abstracts: bool) -> list[BackendRecord]:
        if not isinstance(payload, list):
            return []
        return [
            record
            for item in payload
            if (record := self._record(item, include_abstracts))
        ]

    def _record(self, item: object, include_abstracts: bool) -> BackendRecord | None:
        if not isinstance(item, dict) or not clean_text(item.get("title")):
            return None
        external_value = item.get("externalIds")
        external = (
            cast(dict[str, Any], external_value)
            if isinstance(external_value, dict)
            else {}
        )
        paper_id = item.get("paperId")
        if not isinstance(paper_id, str) or not paper_id:
            return None
        authors = _name_list(item.get("authors"))
        access_value = item.get("openAccessPdf")
        access = (
            cast(dict[str, Any], access_value) if isinstance(access_value, dict) else {}
        )
        title = clean_text(item.get("title"), limit=2_000)
        if not title:
            return None
        work = Work(
            title=title,
            authors=authors,
            year=_year(item.get("year")),
            doi=external.get("DOI"),
            arxiv_id=external.get("ArXiv"),
            s2_id=paper_id,
            abstract=item.get("abstract") if include_abstracts else None,
            venue=item.get("venue"),
            url=item.get("url"),
            pdf_url=access.get("url"),
        )
        return BackendRecord(self.name, paper_id, work, item)


class CrossrefBackend:
    name = "crossref"
    endpoint = "https://api.crossref.org/works"
    _search_cap = 1_000

    def __init__(self, http: HttpClient, mailto: str | None = None) -> None:
        self.http = http
        self.mailto = mailto or os.getenv("CROSSREF_MAILTO")

    def _params(self, params: Mapping[str, object]) -> dict[str, object]:
        return {**params, **({"mailto": self.mailto} if self.mailto else {})}

    def search(
        self, query: str, limit: int, include_abstracts: bool
    ) -> list[BackendRecord]:
        payload = _json(
            self.http.request(
                "GET",
                self.endpoint,
                params=self._params(
                    {"query.bibliographic": query, "rows": min(limit, self._search_cap)}
                ),
            ),
            self.name,
        )
        message_value = payload.get("message")
        message = (
            cast(dict[str, Any], message_value)
            if isinstance(message_value, dict)
            else {}
        )
        return self._records(message.get("items"), include_abstracts)

    def resolve(self, identifier: Identifier) -> list[BackendRecord]:
        if identifier.kind != "doi":
            return []
        payload = _json(
            self.http.request(
                "GET",
                f"{self.endpoint}/{quote(identifier.value, safe='')}",
                params=self._params({}),
            ),
            self.name,
        )
        message_value = payload.get("message")
        message = (
            cast(dict[str, Any], message_value)
            if isinstance(message_value, dict)
            else {}
        )
        return self._records([message], True)

    def _records(self, payload: object, include_abstracts: bool) -> list[BackendRecord]:
        if not isinstance(payload, list):
            return []
        records: list[BackendRecord] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            title_values = item.get("title")
            title = (
                title_values[0]
                if isinstance(title_values, list) and title_values
                else None
            )
            doi = item.get("DOI")
            if not isinstance(title, str) or not isinstance(doi, str):
                continue
            author_values = item.get("author")
            authors: list[str] = []
            if isinstance(author_values, list):
                for author in author_values:
                    if isinstance(author, dict):
                        name = " ".join(
                            str(author.get(part, "")) for part in ("given", "family")
                        ).strip()
                        if name:
                            authors.append(name)
            pdf_url = None
            for link in (
                item.get("link", []) if isinstance(item.get("link"), list) else []
            ):
                if (
                    isinstance(link, dict)
                    and link.get("content-type") == "application/pdf"
                ):
                    pdf_url = link.get("URL")
                    break
            work = Work(
                title=title,
                authors=tuple(authors),
                year=_crossref_year(item),
                doi=doi,
                abstract=item.get("abstract") if include_abstracts else None,
                venue=(item.get("container-title") or [None])[0]
                if isinstance(item.get("container-title"), list)
                else None,
                url=item.get("URL"),
                pdf_url=pdf_url,
            )
            if work.doi:
                records.append(BackendRecord(self.name, work.doi, work, item))
        return records


def _crossref_year(item: dict[str, Any]) -> int | None:
    for field in ("published-print", "published-online", "issued", "created"):
        value = item.get(field)
        parts = value.get("date-parts") if isinstance(value, dict) else None
        if (
            isinstance(parts, list)
            and parts
            and isinstance(parts[0], list)
            and parts[0]
        ):
            return _year(parts[0][0])
    return None


class BackendManager:
    """Coordinates selected adapters while preserving partial-source errors."""

    def __init__(self, http: HttpClient | None = None) -> None:
        self.http = http or HttpClient()
        self._owns_http = http is None
        self.backends = {
            "arxiv": ArxivBackend(self.http),
            "openalex": OpenAlexBackend(self.http),
            "semantic-scholar": SemanticScholarBackend(self.http),
            "crossref": CrossrefBackend(self.http),
        }

    def close(self) -> None:
        if self._owns_http:
            self.http.close()

    def __enter__(self) -> "BackendManager":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def credentials() -> dict[str, bool]:
        return {
            "crossref_mailto": bool(os.getenv("CROSSREF_MAILTO")),
            "openalex_api_key": bool(os.getenv("OPENALEX_API_KEY")),
            "semantic_scholar_api_key": bool(os.getenv("SEMANTIC_SCHOLAR_API_KEY")),
        }

    def search(
        self, query: str, sources: Sequence[str], limit: int, include_abstracts: bool
    ) -> tuple[list[BackendRecord], list[str]]:
        records: list[BackendRecord] = []
        errors: list[str] = []
        for index, name in enumerate(sources):
            remaining = limit - len(records)
            if remaining <= 0:
                break
            # Reserve a fair share for every remaining source. If an earlier
            # backend returns fewer papers than its share, later sources inherit
            # the unused budget without allowing one source to monopolize recall.
            source_budget = math.ceil(remaining / (len(sources) - index))
            backend = self.backends[name]
            try:
                records.extend(
                    backend.search(query, source_budget, include_abstracts)[
                        :source_budget
                    ]
                )
            except BackendError as error:
                errors.append(f"{name}: {error}")
        return records, errors

    def resolve(self, identifier: Identifier) -> tuple[list[BackendRecord], list[str]]:
        records: list[BackendRecord] = []
        errors: list[str] = []
        candidates = {
            "doi": ("crossref", "openalex", "semantic-scholar"),
            "arxiv": ("arxiv", "semantic-scholar"),
            "openalex": ("openalex",),
            "s2": ("semantic-scholar",),
            "corpus": ("semantic-scholar",),
        }[identifier.kind]
        for name in candidates:
            try:
                records.extend(self.backends[name].resolve(identifier))
            except BackendError as error:
                errors.append(f"{name}: {error}")
        return records, errors

    def graph(
        self, identifier: Identifier, direction: str, depth: int, limit: int
    ) -> tuple[list[CitationEdge], list[str]]:
        if depth != 1:
            raise ValueError("only --depth 1 is supported in v1")
        names = (
            ("openalex",)
            if identifier.kind == "openalex"
            else ("semantic-scholar", "openalex")
        )
        edges: list[CitationEdge] = []
        errors: list[str] = []
        for index, name in enumerate(names):
            remaining = limit - len(edges)
            if remaining <= 0:
                break
            # Keep both graph providers represented inside one global edge
            # budget. The second provider is corroborating evidence, not merely
            # a fallback after the first has consumed the entire limit.
            source_budget = math.ceil(remaining / (len(names) - index))
            backend = self.backends[name]
            graph = getattr(backend, "graph", None)
            if graph is None:
                continue
            try:
                edges.extend(
                    graph(identifier, direction, source_budget)[:source_budget]
                )
            except BackendError as error:
                errors.append(f"{name}: {error}")
        return edges, errors
