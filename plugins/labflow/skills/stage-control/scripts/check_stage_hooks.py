#!/usr/bin/env python3
"""Check or enable the Codex feature flags needed by Labflow stage hooks.

This script intentionally uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def config_path(raw: str | None) -> Path:
    return Path(raw).expanduser() if raw else Path.home() / ".codex" / "config.toml"


def section_bounds(lines: list[str], section: str) -> tuple[int, int] | None:
    header = f"[{section}]"
    start = None
    for index, line in enumerate(lines):
        if line.strip() == header:
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = index
            break
    return start, end


def parse_bool_value(raw: str) -> bool | None:
    value = raw.split("#", 1)[0].strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def read_feature(lines: list[str], key: str) -> bool | None:
    bounds = section_bounds(lines, "features")
    if bounds is None:
        return None
    start, end = bounds
    prefix = f"{key}"
    for line in lines[start + 1 : end]:
        stripped = line.strip()
        if stripped.startswith(prefix) and "=" in stripped:
            left, right = stripped.split("=", 1)
            if left.strip() == key:
                return parse_bool_value(right)
    return None


def ensure_feature(lines: list[str], key: str, value: bool = True) -> list[str]:
    desired = f"{key} = {'true' if value else 'false'}\n"
    bounds = section_bounds(lines, "features")
    if bounds is None:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend(["[features]\n", desired])
        return lines

    start, end = bounds
    for index in range(start + 1, end):
        stripped = lines[index].strip()
        if stripped.startswith(key) and "=" in stripped:
            left, _ = stripped.split("=", 1)
            if left.strip() == key:
                lines[index] = desired
                return lines

    insert_at = end
    lines.insert(insert_at, desired)
    return lines


def inspect(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
    hooks = read_feature(lines, "hooks")
    plugin_hooks = read_feature(lines, "plugin_hooks")
    hooks_enabled = hooks is not False
    plugin_hooks_enabled = plugin_hooks is True
    return {
        "config_path": str(path),
        "exists": path.exists(),
        "hooks_enabled": hooks_enabled,
        "plugin_hooks_enabled": plugin_hooks_enabled,
        "needs_write": not hooks_enabled or not plugin_hooks_enabled,
        "notes": [
            "Codex hooks are enabled by default unless [features].hooks = false.",
            "Plugin-bundled hooks require [features].plugin_hooks = true.",
        ],
    }


def write(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True) if path.exists() else []
    lines = ensure_feature(lines, "hooks", True)
    lines = ensure_feature(lines, "plugin_hooks", True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")
    return inspect(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None, help="Path to Codex config.toml")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="Check current hook feature flags")
    group.add_argument("--write", action="store_true", help="Enable required hook feature flags")
    args = parser.parse_args()

    path = config_path(args.config)
    result = write(path) if args.write else inspect(path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
