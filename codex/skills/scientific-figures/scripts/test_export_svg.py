"""Focused tests for the native SVG export helper."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import export_svg


SVG_PREFIX = b'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="120" height="60" viewBox="0 0 120 60">
'''
SVG_SUFFIX = b'''</svg>
'''


class ExportSvgTests(unittest.TestCase):
    """Protect validation and the non-destructive export boundary."""

    def write_svg(self, root: Path, body: bytes, name: str = "master.svg") -> Path:
        source = root / name
        source.write_bytes(SVG_PREFIX + body + SVG_SUFFIX)
        return source

    def test_duplicate_id_and_missing_image_fail_before_overwrite(self) -> None:
        cases = {
            "duplicate.svg": b'<rect id="same"/><circle id="same"/>',
            "missing-image.svg": b'<image id="hand" href="assets/hand.png"/>',
        }
        for name, body in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = self.write_svg(root, body, name)
                pdf = root / f"{source.stem}.pdf"
                preview = root / "preview.png"
                pdf.write_bytes(b"old-pdf")
                preview.write_bytes(b"old-preview")
                before = (pdf.read_bytes(), preview.read_bytes())

                with self.assertRaises(export_svg.SvgValidationError):
                    export_svg.run_export(source)

                self.assertEqual((pdf.read_bytes(), preview.read_bytes()), before)

    def test_missing_internal_reference_and_foreign_object_are_explicit(self) -> None:
        body = (
            b'<defs><clipPath id="clip"><rect width="20" height="20"/></clipPath></defs>'
            b'<rect style="clip-path:url(#missing)" width="20" height="20"/>'
            b'<foreignObject width="10" height="10"><div/></foreignObject>'
        )
        with tempfile.TemporaryDirectory() as temporary:
            source = self.write_svg(Path(temporary), body)
            with self.assertRaises(export_svg.SvgValidationError) as raised:
                export_svg.run_export(source, check_only=True)
        message = "\n".join(raised.exception.issues)
        self.assertIn("missing internal SVG reference", message)
        self.assertIn("foreignObject", message)

    def test_external_anchor_is_not_treated_as_an_image_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = self.write_svg(
                Path(temporary),
                b'<a href="https://example.com/paper"><text id="link">Paper</text></a>',
            )
            info = export_svg.validate_svg(source)
        self.assertEqual(info.input_dependencies, ())
        self.assertEqual(info.image_count, 0)

    def test_inkscape_failure_preserves_existing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.write_svg(root, b'<text id="label">Keep this text</text>')
            pdf = root / "master.pdf"
            preview = root / "preview.png"
            pdf.write_bytes(b"previous-pdf")
            preview.write_bytes(b"previous-preview")
            before_source = source.read_bytes()
            before_outputs = (pdf.read_bytes(), preview.read_bytes())
            failed = subprocess.CompletedProcess(
                args=["inkscape"], returncode=17, stdout="", stderr="renderer failed"
            )
            with mock.patch.object(export_svg.shutil, "which", return_value="inkscape"), mock.patch.object(
                export_svg.subprocess, "run", return_value=failed
            ):
                with self.assertRaises(export_svg.SvgExportError):
                    export_svg.run_export(source)
            self.assertEqual(source.read_bytes(), before_source)
            self.assertEqual((pdf.read_bytes(), preview.read_bytes()), before_outputs)

    def test_failed_rollback_keeps_durable_recovery_copies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pdf = root / "master.pdf"
            preview = root / "preview.png"
            pdf.write_bytes(b"original-pdf")
            preview.write_bytes(b"original-preview")
            stage = root / "stage"
            stage.mkdir()
            staged_pdf = stage / pdf.name
            staged_preview = stage / preview.name
            staged_pdf.write_bytes(b"new-pdf")
            staged_preview.write_bytes(b"new-preview")

            real_replace = export_svg.os.replace

            def fail_second_promotion_and_rollback(source: Path, destination: Path) -> None:
                source = Path(source)
                destination = Path(destination)
                if source == staged_preview or source.parent.name.startswith(
                    ".export-svg-recovery-"
                ):
                    raise OSError("simulated second promotion/rollback failure")
                real_replace(source, destination)

            with mock.patch.object(
                export_svg.os, "replace", side_effect=fail_second_promotion_and_rollback
            ):
                with self.assertRaises(export_svg.SvgExportError) as raised:
                    export_svg._promote_outputs(
                        {pdf: staged_pdf, preview: staged_preview}
                    )

            message = str(raised.exception)
            self.assertIn("recoverable in", message)
            recovery_dirs = list(root.glob(".export-svg-recovery-*"))
            self.assertEqual(len(recovery_dirs), 1)
            recovery = recovery_dirs[0]
            self.assertEqual((recovery / pdf.name).read_bytes(), b"original-pdf")
            self.assertEqual((recovery / preview.name).read_bytes(), b"original-preview")
            self.assertEqual(preview.read_bytes(), b"original-preview")

    def test_successful_exports_report_inkscape_stderr(self) -> None:
        pdf_bytes = b"%PDF-1.7\n%%EOF\n"
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            + b"\x00" * 8
            + (320).to_bytes(4, "big")
            + (160).to_bytes(4, "big")
            + b"IEND"
        )

        def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            output = next(
                Path(argument.split("=", 1)[1])
                for argument in command
                if argument.startswith("--export-filename=")
            )
            output.write_bytes(pdf_bytes if output.suffix == ".pdf" else png_bytes)
            stage = "pdf" if output.suffix == ".pdf" else "preview"
            return subprocess.CompletedProcess(command, 0, stdout="", stderr=f"warning-{stage}")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.write_svg(root, b'<text id="label">Keep this text</text>')
            (root / "master.pdf").write_bytes(b"old-pdf")
            (root / "preview.png").write_bytes(b"old-preview")
            with mock.patch.object(export_svg.shutil, "which", return_value="inkscape"), mock.patch.object(
                export_svg.subprocess, "run", side_effect=fake_run
            ):
                result = export_svg.run_export(source)
            self.assertEqual(list(root.glob(".export-svg-recovery-*")), [])
        self.assertEqual(
            result["inkscape_stderr"],
            {"pdf": "warning-pdf", "preview_png": "warning-preview"},
        )

    @unittest.skipUnless(shutil.which("inkscape"), "Inkscape is not installed")
    def test_real_inkscape_export_preserves_master_text_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.write_svg(
                root,
                b'<rect id="box" width="120" height="60" fill="#f4f4f4"/>'
                b'<text id="label" x="10" y="35">Keep this text</text>',
            )
            before = source.read_bytes()
            result = export_svg.run_export(source, preview_width=320)
            self.assertEqual(result["status"], "exported")
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue((root / "master.pdf").read_bytes().startswith(b"%PDF-"))
            self.assertTrue((root / "preview.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
