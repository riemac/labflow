#!/usr/bin/env python3
"""Install regular worker TOML copies without overwriting user customizations.

Codex 0.153.4 discovers symlinked roles but rejects them during role loading.
The checksum ledger distinguishes an unchanged managed copy from a file edited
by the user. Only an exact legacy source symlink is migrated automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import tomllib


WORKERS = ("learning-worker", "literature-worker", "paper-editor", "paper-reviewer")
REVIEW_SKILLS = ("paper-writing", "scientific-figures")


def atomic_write(path: Path, data: bytes) -> None:
    """Replace the destination entry, never write through an existing symlink."""
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _version_key(path: Path) -> tuple[tuple[int, object], ...]:
    """Sort cache directory names with numeric version components in order."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", path.name)
    )


def resolve_installed_skill_root(
    cache_root: Path,
    required_skills: tuple[str, ...] = REVIEW_SKILLS,
) -> Path | None:
    """Return the newest installed cache ``skills`` directory that is complete."""
    if not cache_root.is_dir():
        return None
    versions = sorted(
        (entry for entry in cache_root.iterdir() if entry.is_dir()),
        key=_version_key,
    )
    for version in reversed(versions):
        skill_root = version / "skills"
        if all((skill_root / name / "SKILL.md").is_file() for name in required_skills):
            return skill_root.resolve()
    return None


def _inject_skill_paths(data: bytes, skill_root: Path) -> bytes:
    """Point reviewer skill toggles at the actual installed cache files."""
    text = data.decode()
    for skill_name in REVIEW_SKILLS:
        pattern = re.compile(
            rf'(?m)^(?P<prefix>\s*path\s*=\s*")[^"\n]*'
            rf'/skills/{re.escape(skill_name)}/SKILL\.md(?P<suffix>"\s*)$'
        )
        replacement = str(skill_root / skill_name / "SKILL.md").replace("\\", "\\\\").replace('"', '\\"')
        text = pattern.sub(rf'\g<prefix>{replacement}\g<suffix>', text)
    return text.encode()


def _prepare_payload(name: str, source: Path, skill_root: Path) -> bytes:
    """Prepare one role while keeping reviewer-only skill handling scoped."""
    data = source.read_bytes()
    if name == "paper-reviewer":
        return _inject_skill_paths(data, skill_root)
    return data


def _validate_reviewer_skill_config(data: bytes, skill_root: Path) -> None:
    """Fail closed unless the reviewer disables exactly the two author skills."""
    role = tomllib.loads(data.decode())
    configs = role.get("skills", {}).get("config", [])
    expected = [
        str(skill_root / name / "SKILL.md")
        for name in REVIEW_SKILLS
    ]
    actual = [entry.get("path") for entry in configs]
    if len(configs) != len(REVIEW_SKILLS) or actual != expected:
        raise ValueError("paper-reviewer skill paths were not injected exactly")
    if any(entry.get("enabled") is not False for entry in configs):
        raise ValueError("paper-reviewer author skills must be disabled")
    if any(not Path(path).is_file() for path in actual):
        raise FileNotFoundError("paper-reviewer skill path does not exist")


def install_workers(
    source_dir: Path,
    target_dir: Path,
    *,
    skill_root: Path | None = None,
    cache_root: Path | None = None,
) -> dict[str, str]:
    """Install all tracked roles, preserving unknown files and user edits."""
    if skill_root is not None and cache_root is not None:
        raise ValueError("pass skill_root or cache_root, not both")
    if cache_root is not None:
        skill_root = resolve_installed_skill_root(cache_root)
        if skill_root is None:
            raise FileNotFoundError(
                f"no complete installed skill cache under {cache_root}"
            )
    if skill_root is None:
        skill_root = (source_dir.resolve().parent / "skills")
    sources = {name: source_dir / f"{name}.toml" for name in WORKERS}
    payloads = {
        name: _prepare_payload(name, source, skill_root)
        for name, source in sources.items()
    }
    # Validate every source before modifying either role or the ownership ledger.
    for name, data in payloads.items():
        role = tomllib.loads(data.decode())
        if role.get("name") != name or not role.get("developer_instructions"):
            raise ValueError(f"Invalid worker source: {sources[name]}")
        if name == "paper-reviewer":
            _validate_reviewer_skill_config(data, skill_root)
    target_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = target_dir / ".labflow-managed.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
    results = {}
    for name, source in sources.items():
        target = target_dir / f"{name}.toml"
        expected = ledger.get(name)
        # Only a link to this exact tracked template belongs to the old installer.
        if target.is_symlink():
            owned = target.resolve() == source.resolve()
        elif target.exists():
            owned = target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected
        else:
            owned = True
        if not owned:
            results[name] = "preserved user-owned or modified file"
            continue
        atomic_write(target, payloads[name])
        ledger[name] = hashlib.sha256(payloads[name]).hexdigest()
        results[name] = "installed managed regular file"
    atomic_write(ledger_path, (json.dumps(ledger, indent=2) + "\n").encode())
    return results


def main() -> None:
    """Accept explicit source, destination, and installed-cache paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--target-dir", required=True, type=Path)
    parser.add_argument(
        "--skill-root",
        type=Path,
        help="actual installed plugin skills directory",
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        help="plugin cache containing version directories; newest complete skills are selected",
    )
    args = parser.parse_args()
    if args.skill_root is not None and args.cache_root is not None:
        parser.error("--skill-root and --cache-root are mutually exclusive")
    for name, result in install_workers(
        args.source_dir,
        args.target_dir,
        skill_root=args.skill_root,
        cache_root=args.cache_root,
    ).items():
        print(f"{name}: {result}")


if __name__ == "__main__":
    main()
