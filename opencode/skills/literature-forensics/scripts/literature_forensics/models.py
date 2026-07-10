"""Normalized, validated data models shared by every backend and exporter."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any
from urllib.parse import unquote, urlsplit


class ValidationError(ValueError):
    """Raised when user input or remote metadata is unsuitable for use."""


_DOI_PREFIX_RE = re.compile(r"^10\.\d{4,9}/", re.IGNORECASE)
_ARXIV_RE = re.compile(
    r"^(?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z-]+)?/\d{7})(?:v\d+)?$",
    re.IGNORECASE,
)
_OPENALEX_RE = re.compile(r"^W\d+$", re.IGNORECASE)
_S2_RE = re.compile(r"^[a-z0-9-]{8,128}$", re.IGNORECASE)
_CORPUS_RE = re.compile(r"^\d+$")


def clean_text(value: object, *, limit: int = 20_000) -> str:
    """Collapse untrusted text to a bounded single-line representation."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


def normalize_title(value: object) -> str:
    """Return a conservative title key for the final deduplication fallback."""
    text = clean_text(value, limit=2_000).casefold()
    return re.sub(r"[^\w]+", " ", text, flags=re.UNICODE).strip()


def normalize_doi(value: object) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 1_024:
        return None
    doi = unquote(value)
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", "", doi, flags=re.I)
    if not _DOI_PREFIX_RE.match(doi) or any(
        ord(char) < 33 or ord(char) > 126 for char in doi
    ):
        return None
    suffix = doi.split("/", 1)[1]
    # DOI suffixes legitimately use punctuation such as <>[]; do not strip it.
    # Backslashes and dot-only path segments are neither portable nor useful here.
    if (
        not suffix
        or "\\" in suffix
        or suffix.startswith("/")
        or any(part in {".", ".."} for part in suffix.split("/"))
    ):
        return None
    return doi.lower()


def normalize_arxiv(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    arxiv_id = value.strip()
    arxiv_id = re.sub(
        r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv:\s*)", "", arxiv_id, flags=re.I
    )
    arxiv_id = arxiv_id.removesuffix(".pdf").split("?")[0].strip()
    if not _ARXIV_RE.fullmatch(arxiv_id):
        return None
    return re.sub(r"v\d+$", "", arxiv_id, flags=re.IGNORECASE).lower()


def normalize_openalex(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    identifier = value.strip().rstrip("/").rsplit("/", 1)[-1]
    identifier = re.sub(r"^openalex:\s*", "", identifier, flags=re.I)
    return identifier.upper() if _OPENALEX_RE.fullmatch(identifier) else None


def normalize_s2(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    identifier = re.sub(r"^(?:s2|semanticscholar):\s*", "", value.strip(), flags=re.I)
    return identifier if _S2_RE.fullmatch(identifier) else None


def safe_https_url(value: object) -> str | None:
    """Only retain simple HTTPS URLs suitable for displaying or downloading."""
    if (
        not isinstance(value, str)
        or len(value) > 8_192
        or any(char.isspace() for char in value)
    ):
        return None
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        return None
    return value


@dataclass(frozen=True, slots=True)
class Identifier:
    kind: str
    value: str

    @property
    def api_value(self) -> str:
        if self.kind == "doi":
            return f"DOI:{self.value}"
        if self.kind == "arxiv":
            return f"ARXIV:{self.value}"
        if self.kind == "corpus":
            return f"CorpusId:{self.value}"
        return self.value


def parse_identifier(value: str) -> Identifier:
    """Recognize only identifiers handled by one of the supported APIs."""
    raw = clean_text(value, limit=1_000)
    if not raw:
        raise ValidationError("identifier must not be empty")
    doi = normalize_doi(raw)
    if doi:
        return Identifier("doi", doi)
    arxiv_id = normalize_arxiv(raw)
    if arxiv_id:
        return Identifier("arxiv", arxiv_id)
    openalex_id = normalize_openalex(raw)
    if openalex_id:
        return Identifier("openalex", openalex_id)
    corpus = re.sub(r"^corpusid:\s*", "", raw, flags=re.I)
    if _CORPUS_RE.fullmatch(corpus):
        return Identifier("corpus", corpus)
    s2_id = normalize_s2(raw)
    if s2_id:
        return Identifier("s2", s2_id)
    raise ValidationError(
        "identifier must be a DOI, arXiv, OpenAlex, Semantic Scholar, or CorpusId identifier"
    )


@dataclass(frozen=True, slots=True)
class Work:
    """Source-independent paper metadata with compact, validated fields."""

    title: str
    authors: tuple[str, ...] = ()
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    openalex_id: str | None = None
    s2_id: str | None = None
    abstract: str | None = None
    venue: str | None = None
    url: str | None = None
    pdf_url: str | None = None

    def __post_init__(self) -> None:
        title = clean_text(self.title, limit=2_000)
        if not title:
            raise ValidationError("work title must not be empty")
        object.__setattr__(self, "title", title)
        object.__setattr__(
            self,
            "authors",
            tuple(
                clean_text(author, limit=300)
                for author in self.authors
                if clean_text(author, limit=300)
            ),
        )
        if self.year is not None and not 1000 <= self.year <= 3000:
            object.__setattr__(self, "year", None)
        object.__setattr__(self, "doi", normalize_doi(self.doi))
        object.__setattr__(self, "arxiv_id", normalize_arxiv(self.arxiv_id))
        object.__setattr__(self, "openalex_id", normalize_openalex(self.openalex_id))
        object.__setattr__(self, "s2_id", normalize_s2(self.s2_id))
        object.__setattr__(self, "abstract", clean_text(self.abstract) or None)
        object.__setattr__(self, "venue", clean_text(self.venue, limit=1_000) or None)
        object.__setattr__(self, "url", safe_https_url(self.url))
        object.__setattr__(self, "pdf_url", safe_https_url(self.pdf_url))

    @property
    def title_norm(self) -> str:
        return normalize_title(self.title)

    @property
    def identity(self) -> str:
        if self.doi:
            return f"doi:{self.doi}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        if self.openalex_id:
            return f"openalex:{self.openalex_id}"
        if self.s2_id:
            return f"s2:{self.s2_id}"
        digest = sha256(f"{self.title_norm}|{self.year or ''}".encode()).hexdigest()[
            :16
        ]
        return f"title:{digest}"

    @property
    def citekey(self) -> str:
        author = self.authors[0].split()[-1] if self.authors else "anonymous"
        first_word = next(iter(re.findall(r"[A-Za-z0-9]+", self.title)), "work")
        base = re.sub(r"[^a-z0-9]+", "", author.casefold())[:24] or "anonymous"
        word = re.sub(r"[^a-z0-9]+", "", first_word.casefold())[:24] or "work"
        suffix = sha256(self.identity.encode()).hexdigest()[:8]
        return f"{base}_{self.year or 'nd'}_{word}_{suffix}"

    def to_dict(self, *, include_abstract: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "arxiv_id": self.arxiv_id,
            "authors": list(self.authors),
            "citekey": self.citekey,
            "doi": self.doi,
            "identity": self.identity,
            "openalex_id": self.openalex_id,
            "pdf_url": self.pdf_url,
            "s2_id": self.s2_id,
            "title": self.title,
            "url": self.url,
            "venue": self.venue,
            "year": self.year,
        }
        if include_abstract:
            data["abstract"] = self.abstract
        return data


@dataclass(frozen=True, slots=True)
class BackendRecord:
    source: str
    source_id: str
    work: Work
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CitationEdge:
    """A directed edge where `citing` cites `cited`."""

    citing: Work
    cited: Work
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cited": self.cited.identity,
            "citing": self.citing.identity,
            "source": self.source,
        }
