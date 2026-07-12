"""Standard-library tests for deterministic research directory mechanics."""

from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from research import initialize, migrate_v1, validate


class ResearchDirectoryTests(unittest.TestCase):
    """Protect human/audit separation and non-destructive migration behavior."""

    def test_init_and_validate(self) -> None:
        """A fresh Chinese dossier exposes only the intended human entry points."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "research"
            initialize(root, language="zh-CN", title="调研", question="问题是什么？")
            result = validate(root)
            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(result["language"], "zh-CN")
            self.assertTrue((root / "overview.md").is_file())
            self.assertTrue((root / ".research/audit/papers").is_dir())

    def test_migration_moves_agent_material(self) -> None:
        """A v1 dossier preserves evidence while replacing its visible structure."""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "research"
            (root / "papers").mkdir(parents=True)
            (root / "topics").mkdir()
            (root / "README.md").write_text("legacy overview\n", encoding="utf-8")
            (root / "MAP.md").write_text("legacy map\n", encoding="utf-8")
            (root / "brief.md").write_text("legacy brief\n", encoding="utf-8")
            (root / "papers/example.md").write_text(
                'pdf: "example.pdf"\n', encoding="utf-8"
            )
            (root / "papers/example.pdf").write_bytes(b"%PDF-test")
            (root / "topics/lane.md").write_text("lane evidence\n", encoding="utf-8")

            actions = migrate_v1(
                root, language="zh-CN", title="调研", question="问题？", apply=False
            )
            self.assertTrue(
                any(
                    action.destination == ".research/library/example.pdf"
                    for action in actions
                )
            )
            migrate_v1(
                root, language="zh-CN", title="调研", question="问题？", apply=True
            )

            self.assertTrue((root / ".research/audit/legacy-overview.md").is_file())
            self.assertTrue((root / ".research/audit/lanes/lane.md").is_file())
            self.assertTrue((root / ".research/library/example.pdf").is_file())
            self.assertIn(
                "../../library/example.pdf",
                (root / ".research/audit/papers/example.md").read_text(
                    encoding="utf-8"
                ),
            )
            self.assertTrue(validate(root)["ok"])


if __name__ == "__main__":
    unittest.main()
