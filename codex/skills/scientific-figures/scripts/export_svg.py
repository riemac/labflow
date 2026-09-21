#!/usr/bin/env python3
"""Validate a native SVG and export a reproducible PDF plus PNG preview.

This helper deliberately keeps the SVG as the editable master.  It validates
references before invoking Inkscape, exports into a private temporary
directory, and installs both outputs only after both exports and basic format
checks succeed.  It does not rewrite the source SVG or make visual-quality
claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Iterable, Sequence
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
_XLINK_NAMESPACE = "http://www.w3.org/1999/xlink"


class SvgValidationError(Exception):
    """Raised when the SVG cannot be safely handed to the export command."""

    def __init__(self, issues: Sequence[str], info: "SvgInfo | None" = None):
        self.issues = tuple(issues)
        self.info = info
        super().__init__("; ".join(self.issues))


class SvgExportError(Exception):
    """Raised when Inkscape or output installation fails."""


@dataclass(frozen=True)
class SvgInfo:
    """Small, source-derived summary used in the machine-readable report."""

    source: Path
    source_sha256: str
    text_count: int
    image_count: int
    foreign_object_count: int
    input_dependencies: tuple[Path, ...]
    dimensions: dict[str, str | None]


def _local_name(tag_or_attribute: object) -> str:
    """Return an XML local name for namespaced and unnamespaced values."""

    if not isinstance(tag_or_attribute, str):
        return ""
    return tag_or_attribute.rsplit("}", 1)[-1].split(":", 1)[-1]


def _element_label(element: ET.Element) -> str:
    """Return a compact element description suitable for diagnostics."""

    name = _local_name(element.tag) or "element"
    element_id = element.attrib.get("id")
    return f"<{name} id={element_id!r}>" if element_id else f"<{name}>"


def _href_attributes(element: ET.Element) -> list[tuple[str, str]]:
    """Collect ordinary and xlink href attributes without losing provenance."""

    hrefs: list[tuple[str, str]] = []
    for attribute, value in element.attrib.items():
        if attribute == "href" or attribute == f"{{{_XLINK_NAMESPACE}}}href":
            hrefs.append((attribute, value))
    return hrefs


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_network_uri(value: str) -> bool:
    """Identify URI forms that could cause a renderer to access the network."""

    parsed = urlsplit(value)
    return value.startswith("//") or parsed.scheme.lower() in {
        "http",
        "https",
        "ftp",
        "ftps",
    }


def _local_dependency_from_href(value: str, source: Path) -> Path | None:
    """Resolve a local image href, returning None for embedded/internal data."""

    raw = value.strip()
    if not raw or raw.startswith("#") or raw.lower().startswith("data:"):
        return None

    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if _is_network_uri(raw):
        raise SvgValidationError(
            [f"external image resource is not allowed: {raw!r}; embed it or use a local file"]
        )
    if scheme and scheme != "file":
        raise SvgValidationError(
            [f"unsupported image URI scheme {scheme!r}: {raw!r}; use a local file or data URI"]
        )
    if scheme == "file":
        if parsed.netloc not in ("", "localhost"):
            raise SvgValidationError(
                [f"file URI with a remote host is not allowed: {raw!r}"]
            )
        image_name = unquote(parsed.path)
    else:
        image_name = unquote(parsed.path)
    if not image_name:
        return None

    image_path = Path(image_name)
    if not image_path.is_absolute():
        image_path = source.parent / image_path
    return image_path.resolve()


def _internal_url_references(value: str) -> Iterable[str]:
    """Yield IDs from url(#id) expressions in an attribute or style block."""

    for match in _URL_RE.finditer(value):
        target = match.group(2).strip()
        if target.startswith("#") and len(target) > 1:
            yield target[1:]


def _external_url_references(value: str) -> Iterable[str]:
    """Yield network URLs embedded in CSS-like url(...) expressions."""

    for match in _URL_RE.finditer(value):
        target = match.group(2).strip()
        if _is_network_uri(target):
            yield target


def _parse_source(source: Path) -> tuple[ET.Element, bytes, str]:
    """Read and parse source bytes without enabling external resource loading."""

    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise SvgExportError(f"cannot read SVG source {source}: {exc}") from exc
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SvgValidationError([f"invalid SVG XML: {exc}"]) from exc
    if _local_name(root.tag).lower() != "svg":
        raise SvgValidationError([f"SVG root must be <svg>, found {_element_label(root)}"])
    return root, raw, hashlib.sha256(raw).hexdigest()


def validate_svg(source: Path | str) -> SvgInfo:
    """Validate source structure and local image inputs before export."""

    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise SvgExportError(f"SVG source is not a regular file: {source_path}")

    root, _raw, source_sha256 = _parse_source(source_path)
    ids: dict[str, list[str]] = {}
    elements = list(root.iter())
    for element in elements:
        element_id = element.attrib.get("id")
        if element_id:
            ids.setdefault(element_id, []).append(_element_label(element))

    issues: list[str] = []
    for element_id, locations in ids.items():
        if len(locations) > 1:
            issues.append(
                f"duplicate SVG id {element_id!r} appears {len(locations)} times"
            )

    dependencies: list[Path] = []
    dependency_keys: set[Path] = set()
    internal_references: list[tuple[str, str]] = []
    for element in elements:
        label = _element_label(element)
        for attribute, value in element.attrib.items():
            for reference in _internal_url_references(value):
                internal_references.append((reference, f"{label} attribute {attribute!r}"))
            for external_url in _external_url_references(value):
                issues.append(
                    f"external url() resource is not allowed: {external_url!r} in {label}"
                )
            if _local_name(attribute) == "href" and value.strip().startswith("#"):
                fragment = value.strip()[1:]
                if fragment:
                    internal_references.append((fragment, f"{label} attribute {attribute!r}"))

        if _local_name(element.tag).lower() == "style":
            style_text = element.text or ""
            for reference in _internal_url_references(style_text):
                internal_references.append((reference, f"{label} text"))
            for external_url in _external_url_references(style_text):
                issues.append(
                    f"external url() resource is not allowed: {external_url!r} in {label}"
                )

        if _local_name(element.tag).lower() != "image":
            continue
        hrefs = _href_attributes(element)
        if not hrefs:
            issues.append(f"{label} has no href or xlink:href image input")
            continue
        distinct_hrefs = {value.strip() for _attribute, value in hrefs}
        if len(distinct_hrefs) > 1:
            issues.append(f"{label} has conflicting href and xlink:href image inputs")
            continue
        try:
            dependency = _local_dependency_from_href(hrefs[0][1], source_path)
        except SvgValidationError as exc:
            issues.extend(exc.issues)
            continue
        if dependency is None:
            continue
        if dependency not in dependency_keys:
            dependency_keys.add(dependency)
            dependencies.append(dependency)
        if not dependency.is_file():
            issues.append(f"missing local image dependency: {dependency}")

    for reference, location in internal_references:
        if reference not in ids:
            issues.append(f"missing internal SVG reference #{reference!r} from {location}")

    foreign_object_count = sum(
        1 for element in elements if _local_name(element.tag).lower() == "foreignobject"
    )
    if foreign_object_count:
        issues.append(
            f"SVG contains {foreign_object_count} foreignObject element(s); "
            "Inkscape export is not assumed lossless for HTML/draw.io content, "
            "so preserve the SVG master and use a renderer validated for this asset"
        )

    info = SvgInfo(
        source=source_path,
        source_sha256=source_sha256,
        text_count=sum(1 for element in elements if _local_name(element.tag).lower() == "text"),
        image_count=sum(1 for element in elements if _local_name(element.tag).lower() == "image"),
        foreign_object_count=foreign_object_count,
        input_dependencies=tuple(dependencies),
        dimensions={
            "width": root.attrib.get("width"),
            "height": root.attrib.get("height"),
            "viewBox": root.attrib.get("viewBox") or root.attrib.get("viewbox"),
        },
    )
    if issues:
        raise SvgValidationError(issues, info=info)
    return info


def _summary(
    info: SvgInfo,
    *,
    status: str,
    pdf: Path,
    preview_png: Path,
    preview_width: int,
    inkscape_stderr: dict[str, str] | None = None,
) -> dict[str, object]:
    """Build the concise machine-readable report shared by check/export modes."""

    return {
        "status": status,
        "source": str(info.source),
        "source_sha256": info.source_sha256,
        "text_count": info.text_count,
        "image_count": info.image_count,
        "foreign_object_count": info.foreign_object_count,
        "input_dependencies": [str(path) for path in info.input_dependencies],
        "dimensions": info.dimensions,
        "preview_width": preview_width,
        "inkscape_stderr": inkscape_stderr or {},
        "outputs": {"pdf": str(pdf), "preview_png": str(preview_png)},
    }


def _short_diagnostic(value: str) -> str:
    """Keep a useful bounded diagnostic without flooding the JSON report."""

    diagnostic = value.strip()
    if len(diagnostic) <= 1200:
        return diagnostic
    return diagnostic[:580] + "\n...[truncated]...\n" + diagnostic[-580:]


def _run_inkscape(command: Sequence[str], source: Path) -> str:
    """Run one export with argv directly and return bounded stderr diagnostics."""

    try:
        completed = subprocess.run(
            list(command),
            cwd=source.parent,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise SvgExportError(f"could not start Inkscape: {exc}") from exc
    stderr_diagnostic = _short_diagnostic(completed.stderr or "")
    if completed.returncode == 0:
        return stderr_diagnostic
    diagnostic = stderr_diagnostic or _short_diagnostic(completed.stdout or "")
    suffix = f": {diagnostic}" if diagnostic else ""
    raise SvgExportError(
        f"Inkscape export failed with exit code {completed.returncode}{suffix}"
    )


def _check_pdf(path: Path) -> None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SvgExportError(f"Inkscape did not produce PDF output {path}: {exc}") from exc
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-4096:]:
        raise SvgExportError(f"invalid PDF export produced at {path}")


def _check_png(path: Path) -> None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise SvgExportError(f"Inkscape did not produce PNG output {path}: {exc}") from exc
    if len(data) < 24 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise SvgExportError(f"invalid PNG preview produced at {path}")
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        raise SvgExportError(f"PNG preview has invalid dimensions at {path}")
    if b"IEND" not in data[-32:]:
        raise SvgExportError(f"PNG preview is missing its IEND chunk at {path}")


def _promote_outputs(staged: dict[Path, Path]) -> None:
    """Install outputs while retaining durable recovery copies on rollback failure."""

    destinations = list(staged)
    existing = [destination for destination in destinations if os.path.lexists(destination)]
    recovery_dir: Path | None = None
    backups: dict[Path, Path] = {}
    if existing:
        try:
            recovery_dir = Path(
                tempfile.mkdtemp(
                    prefix=".export-svg-recovery-",
                    dir=str(destinations[0].parent),
                )
            )
            for destination in existing:
                backup = recovery_dir / destination.name
                shutil.copy2(destination, backup)
                backups[destination] = backup
        except Exception as exc:
            if recovery_dir is not None:
                shutil.rmtree(recovery_dir, ignore_errors=True)
            raise SvgExportError(f"could not prepare output recovery copies: {exc}") from exc

    promoted: list[Path] = []
    try:
        for destination, temporary in staged.items():
            os.replace(temporary, destination)
            promoted.append(destination)
    except Exception as exc:
        rollback_failures: list[str] = []
        for destination in reversed(promoted):
            backup = backups.get(destination)
            if backup is None:
                try:
                    if os.path.lexists(destination):
                        os.unlink(destination)
                except OSError as rollback_exc:
                    rollback_failures.append(f"remove {destination}: {rollback_exc}")
                continue
            try:
                # Moving the durable copy back leaves it available if this
                # operation itself fails; the recovery directory then survives.
                os.replace(backup, destination)
            except OSError as rollback_exc:
                rollback_failures.append(f"restore {destination}: {rollback_exc}")

        if rollback_failures:
            if recovery_dir is None:
                recovery_note = "no previous output files existed to recover"
            else:
                recovery_note = f"old output copies remain recoverable in {recovery_dir}"
            details = "; ".join(rollback_failures)
            raise SvgExportError(
                f"could not install export outputs safely: {exc}; "
                f"rollback also failed ({details}); {recovery_note}"
            ) from exc

        if recovery_dir is not None:
            try:
                shutil.rmtree(recovery_dir)
            except OSError as cleanup_exc:
                raise SvgExportError(
                    f"outputs were restored, but recovery copies remain at "
                    f"{recovery_dir}: {cleanup_exc}"
                ) from cleanup_exc
        raise SvgExportError(f"could not install export outputs safely: {exc}") from exc

    if recovery_dir is not None:
        try:
            shutil.rmtree(recovery_dir)
        except OSError as cleanup_exc:
            raise SvgExportError(
                f"outputs were installed, but recovery copies remain at "
                f"{recovery_dir}: {cleanup_exc}"
            ) from cleanup_exc


def run_export(
    source: Path | str,
    *,
    output_dir: Path | str | None = None,
    preview_width: int = 1600,
    check_only: bool = False,
) -> dict[str, object]:
    """Validate and optionally export ``source``; return the JSON-ready summary."""

    if preview_width <= 0:
        raise SvgExportError("--preview-width must be a positive integer")
    source_path = Path(source).expanduser().resolve()
    destination_dir = (
        source_path.parent
        if output_dir is None
        else Path(output_dir).expanduser().resolve()
    )
    pdf_path = destination_dir / f"{source_path.stem}.pdf"
    preview_path = destination_dir / "preview.png"
    info = validate_svg(source_path)
    if check_only:
        return _summary(
            info,
            status="checked",
            pdf=pdf_path,
            preview_png=preview_path,
            preview_width=preview_width,
        )

    inkscape = shutil.which("inkscape")
    if not inkscape:
        raise SvgExportError(
            "Inkscape executable 'inkscape' was not found; use --check-only or install Inkscape"
        )
    try:
        destination_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SvgExportError(f"cannot create output directory {destination_dir}: {exc}") from exc

    try:
        with tempfile.TemporaryDirectory(
            prefix=".export-svg-", dir=str(destination_dir)
        ) as temporary_name:
            temporary_dir = Path(temporary_name)
            staged_pdf = temporary_dir / pdf_path.name
            staged_preview = temporary_dir / preview_path.name
            inkscape_stderr: dict[str, str] = {}
            pdf_stderr = _run_inkscape(
                [inkscape, str(source_path), f"--export-filename={staged_pdf}"],
                source_path,
            )
            if pdf_stderr:
                inkscape_stderr["pdf"] = pdf_stderr
            _check_pdf(staged_pdf)
            preview_stderr = _run_inkscape(
                [
                    inkscape,
                    str(source_path),
                    f"--export-filename={staged_preview}",
                    f"--export-width={preview_width}",
                ],
                source_path,
            )
            if preview_stderr:
                inkscape_stderr["preview_png"] = preview_stderr
            _check_png(staged_preview)
            if _sha256(source_path) != info.source_sha256:
                raise SvgExportError(
                    "SVG master changed while exporting; existing outputs were preserved"
                )
            _promote_outputs({pdf_path: staged_pdf, preview_path: staged_preview})
    except SvgExportError:
        raise
    except OSError as exc:
        raise SvgExportError(f"export failed without changing existing outputs: {exc}") from exc

    return _summary(
        info,
        status="exported",
        pdf=pdf_path,
        preview_png=preview_path,
        preview_width=preview_width,
        inkscape_stderr=inkscape_stderr,
    )


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a native SVG and export a PDF plus PNG preview with Inkscape."
    )
    parser.add_argument("source", type=Path, help="editable SVG master")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="directory for PDF and preview.png (defaults to the source directory)",
    )
    parser.add_argument(
        "--preview-width",
        type=_positive_int,
        default=1600,
        help="PNG preview width in pixels (default: 1600)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate and print the summary without invoking Inkscape",
    )
    return parser


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _emit(
            run_export(
                args.source,
                output_dir=args.output_dir,
                preview_width=args.preview_width,
                check_only=args.check_only,
            )
        )
    except SvgValidationError as exc:
        payload: dict[str, object] = {
            "status": "error",
            "error": "validation",
            "message": "SVG validation failed; no outputs were changed",
            "issues": list(exc.issues),
        }
        if exc.info is not None:
            payload.update(
                {
                    "source": str(exc.info.source),
                    "text_count": exc.info.text_count,
                    "image_count": exc.info.image_count,
                    "foreign_object_count": exc.info.foreign_object_count,
                    "input_dependencies": [
                        str(path) for path in exc.info.input_dependencies
                    ],
                }
            )
        _emit(payload)
        return 2
    except SvgExportError as exc:
        _emit(
            {
                "status": "error",
                "error": "export",
                "message": str(exc),
            }
        )
        return 1
    except Exception as exc:  # Keep CLI failures machine-readable without a traceback.
        _emit(
            {
                "status": "error",
                "error": "unexpected",
                "message": str(exc),
            }
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
