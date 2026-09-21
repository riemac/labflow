"""Exercise installation ownership and legacy-symlink migration with real files."""

from pathlib import Path
import tempfile
import tomllib
import unittest

from install_workers import WORKERS, install_workers, resolve_installed_skill_root


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class WorkerInstallationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()
        self.target.mkdir()
        for name in ("paper-writing", "scientific-figures"):
            skill = self.root / "skills" / name / "SKILL.md"
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text(f"# {name}\n")
        for name in WORKERS:
            source = self.source / f"{name}.toml"
            content = (
                f'name = "{name}"\n'
                'description = "fixture"\n'
                'developer_instructions = "first"\n'
            )
            if name == "paper-reviewer":
                skill_root = self.root / "skills"
                paper_skill = skill_root / "paper-writing" / "SKILL.md"
                figure_skill = skill_root / "scientific-figures" / "SKILL.md"
                content += (
                    "\n[[skills.config]]\n"
                    f'path = "{paper_skill}"\n'
                    "enabled = false\n\n"
                    "[[skills.config]]\n"
                    f'path = "{figure_skill}"\n'
                    "enabled = false\n\n"
                    "[memories]\nuse_memories = false\ngenerate_memories = false\n"
                )
            source.write_text(content)

    def make_cache(self, version: str) -> Path:
        cache = self.root / "cache"
        skill_root = cache / version / "skills"
        for name in ("paper-writing", "scientific-figures"):
            path = skill_root / name / "SKILL.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {name} {version}\n")
        return cache

    def test_installs_regular_files_and_updates_managed_copies(self):
        install_workers(self.source, self.target)
        source = self.source / "literature-worker.toml"
        source.write_text(source.read_text().replace('"first"', '"second"'))
        install_workers(self.source, self.target)
        for name in WORKERS:
            target = self.target / f"{name}.toml"
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_bytes(), (self.source / target.name).read_bytes())

    def test_migrates_only_matching_legacy_links(self):
        owned = self.target / "learning-worker.toml"
        owned.symlink_to(self.source / owned.name)
        external = self.root / "custom.toml"
        external.write_text("user role")
        unowned = self.target / "literature-worker.toml"
        unowned.symlink_to(external)
        install_workers(self.source, self.target)
        self.assertFalse(owned.is_symlink())
        self.assertTrue(unowned.is_symlink())
        self.assertEqual(external.read_text(), "user role")

    def test_preserves_existing_and_user_modified_files(self):
        custom = self.target / "learning-worker.toml"
        custom.write_text("user-owned")
        install_workers(self.source, self.target)
        modified = self.target / "literature-worker.toml"
        modified.write_text("user-edited managed copy")
        editor = self.target / "paper-editor.toml"
        editor.write_text("user-edited editor copy")
        install_workers(self.source, self.target)
        self.assertEqual(custom.read_text(), "user-owned")
        self.assertEqual(modified.read_text(), "user-edited managed copy")
        self.assertEqual(editor.read_text(), "user-edited editor copy")

    def test_tracked_editor_role_has_fixed_config_and_is_discoverable(self):
        source = REPOSITORY_ROOT / "codex" / "agents" / "paper-editor.toml"
        role = tomllib.loads(source.read_text())
        self.assertIn("paper-editor", WORKERS)
        self.assertEqual(role["name"], "paper-editor")
        self.assertEqual(role["model"], "gpt-5.6-terra")
        self.assertEqual(role["model_reasoning_effort"], "max")
        self.assertEqual(role["sandbox_mode"], "read-only")
        self.assertIn("paper-writing", role["developer_instructions"])
        self.assertNotIn("skills", role)

    def test_editor_does_not_receive_reviewer_skill_injection(self):
        editor = self.source / "paper-editor.toml"
        source_path = self.root / "skills" / "paper-writing" / "SKILL.md"
        editor.write_text(
            editor.read_text()
            + "\n[[skills.config]]\n"
            + f'path = "{source_path}"\n'
            + "enabled = true\n"
        )
        cache = self.make_cache("4.0.0")
        install_workers(self.source, self.target, cache_root=cache)
        role = tomllib.loads(editor.read_text())
        installed = tomllib.loads((self.target / "paper-editor.toml").read_text())
        self.assertEqual(installed["skills"]["config"][0]["path"], str(source_path))
        self.assertTrue(installed["skills"]["config"][0]["enabled"])
        reviewer = tomllib.loads((self.target / "paper-reviewer.toml").read_text())
        self.assertEqual(
            [entry["enabled"] for entry in reviewer["skills"]["config"]],
            [False, False],
        )
        self.assertEqual(role["skills"]["config"][0]["path"], str(source_path))

    def test_invalid_source_leaves_both_targets_unchanged(self):
        install_workers(self.source, self.target)
        before = {p.name: p.read_bytes() for p in self.target.iterdir()}
        (self.source / "literature-worker.toml").write_text("invalid TOML")
        with self.assertRaises(ValueError):
            install_workers(self.source, self.target)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.target.iterdir()})

    def test_resolves_newest_complete_cache_and_injects_actual_skill_paths(self):
        cache = self.make_cache("0.3.0")
        self.make_cache("0.4.0")
        expected_root = resolve_installed_skill_root(cache)
        self.assertEqual(expected_root, (cache / "0.4.0" / "skills").resolve())
        install_workers(self.source, self.target, cache_root=cache)
        role = tomllib.loads((self.target / "paper-reviewer.toml").read_text())
        paths = [entry["path"] for entry in role["skills"]["config"]]
        self.assertEqual(
            paths,
            [
                str(expected_root / "paper-writing" / "SKILL.md"),
                str(expected_root / "scientific-figures" / "SKILL.md"),
            ],
        )

    def test_updates_managed_cache_paths_and_preserves_manual_reviewer_edits(self):
        cache = self.make_cache("1.0.0")
        install_workers(self.source, self.target, cache_root=cache)
        self.make_cache("1.1.0")
        install_workers(self.source, self.target, cache_root=cache)
        updated = (self.target / "paper-reviewer.toml").read_text()
        self.assertIn("/1.1.0/skills/paper-writing/SKILL.md", updated)
        manual = updated + "\n# user customization\n"
        (self.target / "paper-reviewer.toml").write_text(manual)
        self.make_cache("1.2.0")
        result = install_workers(self.source, self.target, cache_root=cache)
        self.assertEqual(result["paper-reviewer"], "preserved user-owned or modified file")
        self.assertEqual((self.target / "paper-reviewer.toml").read_text(), manual)

    def test_incomplete_cache_is_rejected_before_writes(self):
        install_workers(self.source, self.target)
        before = {p.name: p.read_bytes() for p in self.target.iterdir()}
        cache = self.root / "empty-cache"
        (cache / "2.0.0" / "skills" / "paper-writing").mkdir(parents=True)
        with self.assertRaises(FileNotFoundError):
            install_workers(self.source, self.target, cache_root=cache)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.target.iterdir()})

    def test_unmatched_reviewer_path_fails_before_writes(self):
        install_workers(self.source, self.target)
        before = {p.name: p.read_bytes() for p in self.target.iterdir()}
        source = self.source / "paper-reviewer.toml"
        source.write_text(
            source.read_text().replace(
                str(self.root / "skills" / "paper-writing" / "SKILL.md"),
                str(self.root / "unrelated" / "paper-writing" / "SKILL.md"),
            )
        )
        cache = self.make_cache("3.0.0")
        with self.assertRaises(ValueError):
            install_workers(self.source, self.target, cache_root=cache)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.target.iterdir()})


if __name__ == "__main__":
    unittest.main()
