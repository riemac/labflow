"""Explicit, bounded PDF retrieval for metadata already shortlisted in a cache."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import os
import tempfile

from .backends import HttpClient
from .cache import Cache
from .models import Identifier, safe_https_url


MAX_PDF_BYTES = 100 * 1024 * 1024
_PDF_SIGNATURE_WINDOW = 1_024
_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/octet-stream",
}


class DownloadError(ValueError):
    """Raised before an unsafe or unsuccessful PDF download is persisted."""


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def fetch_pdf(
    dossier: Path,
    cache: Cache,
    identifier: Identifier,
    http: HttpClient,
    *,
    force: bool = False,
    max_bytes: int = MAX_PDF_BYTES,
) -> dict[str, object]:
    """Stream one cached work's HTTPS PDF to the dossier's contained papers directory."""
    if not 1 <= max_bytes <= MAX_PDF_BYTES:
        raise DownloadError(
            f"download size cap must be between 1 and {MAX_PDF_BYTES} bytes"
        )
    cached = cache.get_work(identifier)
    if cached is None:
        raise DownloadError(
            "identifier is not cached; search or resolve it before fetch"
        )
    work_id, work = cached
    url = work.pdf_url or (
        f"https://arxiv.org/pdf/{work.arxiv_id}.pdf" if work.arxiv_id else None
    )
    url = safe_https_url(url)
    if not url:
        raise DownloadError("no validated HTTPS PDF URL is cached for this work")
    papers = (dossier / "papers").resolve()
    papers.mkdir(exist_ok=True)
    destination = (papers / f"{work.citekey}.pdf").resolve()
    if not _is_within(destination, papers):
        raise DownloadError("unsafe download path")
    if destination.exists() and not force:
        raise DownloadError(
            f"PDF already exists: {destination.name}; use --force to replace it"
        )

    temporary: Path | None = None
    try:
        with http.stream("GET", url, follow_redirects=True) as response:
            chain = [*response.history, response]
            if any(not safe_https_url(str(item.url)) for item in chain):
                raise DownloadError("PDF redirect chain must remain HTTPS")
            content_type = (
                response.headers.get("Content-Type", "")
                .split(";", 1)[0]
                .strip()
                .lower()
            )
            if content_type and content_type not in _PDF_CONTENT_TYPES:
                raise DownloadError(
                    f"PDF response has unsafe content type: {content_type}"
                )
            length = response.headers.get("Content-Length")
            if length:
                try:
                    announced_size = int(length)
                except ValueError as error:
                    raise DownloadError(
                        "PDF response has an invalid Content-Length"
                    ) from error
                if announced_size < 0 or announced_size > max_bytes:
                    raise DownloadError("PDF exceeds the configured download size cap")
            digest = sha256()
            size = 0
            prefix = bytearray()
            with tempfile.NamedTemporaryFile("wb", dir=papers, delete=False) as handle:
                temporary = Path(handle.name)
                for chunk in response.iter_bytes(chunk_size=64 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise DownloadError(
                            "PDF exceeds the configured download size cap"
                        )
                    if len(prefix) < _PDF_SIGNATURE_WINDOW:
                        prefix.extend(chunk[: _PDF_SIGNATURE_WINDOW - len(prefix)])
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
        if size == 0:
            raise DownloadError("PDF response body is empty")
        if b"%PDF-" not in prefix:
            raise DownloadError(
                "PDF response is missing a PDF signature near the start"
            )
        if not _is_within(temporary, papers):
            raise DownloadError("unsafe temporary download path")
        os.replace(temporary, destination)
        temporary = None
        relative_path = destination.relative_to(dossier.resolve()).as_posix()
        cache.record_download(work_id, url, relative_path, digest.hexdigest(), size)
        return {
            "bytes": size,
            "path": relative_path,
            "sha256": digest.hexdigest(),
            "url": url,
            "work": work.to_dict(include_abstract=False),
        }
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
