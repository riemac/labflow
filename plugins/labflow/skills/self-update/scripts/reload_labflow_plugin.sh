#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  reload_labflow_plugin.sh [--marketplace <id>] [--plugin <name>] [--root <path>]

Reloads the local Labflow Codex plugin by running:
  codex plugin marketplace remove <id>
  codex plugin marketplace add <path>
  codex plugin remove <plugin>@<id>
  codex plugin add <plugin>@<id>

Defaults:
  marketplace id: riemac
  plugin name: labflow
  root: git repository root containing this script, or LABFLOW_MARKETPLACE_ROOT
EOF
}

marketplace_id="${LABFLOW_MARKETPLACE_ID:-riemac}"
plugin_name="${LABFLOW_PLUGIN_NAME:-labflow}"
marketplace_root="${LABFLOW_MARKETPLACE_ROOT:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --marketplace)
      marketplace_id="${2:-}"
      [[ -n "$marketplace_id" ]] || { printf 'Missing value for --marketplace\n' >&2; exit 2; }
      shift 2
      ;;
    --plugin)
      plugin_name="${2:-}"
      [[ -n "$plugin_name" ]] || { printf 'Missing value for --plugin\n' >&2; exit 2; }
      shift 2
      ;;
    --root)
      marketplace_root="${2:-}"
      [[ -n "$marketplace_root" ]] || { printf 'Missing value for --root\n' >&2; exit 2; }
      shift 2
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

command -v codex >/dev/null 2>&1 || {
  printf 'codex CLI not found in PATH.\n' >&2
  exit 1
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "$marketplace_root" ]]; then
  if marketplace_root="$(git -C "$script_dir" rev-parse --show-toplevel 2>/dev/null)"; then
    :
  else
    marketplace_root="$(cd -- "$script_dir/../../../../.." && pwd)"
  fi
fi

[[ -f "$marketplace_root/.agents/plugins/marketplace.json" ]] || {
  printf 'Marketplace root does not look like labflow: %s\n' "$marketplace_root" >&2
  exit 1
}

printf 'Reloading Codex marketplace `%s` from %s\n' "$marketplace_id" "$marketplace_root"

if ! codex plugin marketplace remove "$marketplace_id"; then
  printf 'Marketplace `%s` was not installed; continuing with add.\n' "$marketplace_id" >&2
fi

codex plugin marketplace add "$marketplace_root"

plugin_selector="${plugin_name}@${marketplace_id}"
printf 'Reinstalling Codex plugin `%s`\n' "$plugin_selector"

if ! codex plugin remove "$plugin_selector"; then
  printf 'Plugin `%s` was not installed; continuing with add.\n' "$plugin_selector" >&2
fi

codex plugin add "$plugin_selector"

cache_root="${HOME}/.codex/plugins/cache/${marketplace_id}/${plugin_name}"
if [[ -d "$cache_root" ]]; then
  latest_cache="$(find "$cache_root" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n 1)"
  printf 'Cache updated: %s\n' "${latest_cache:-$cache_root}"
else
  printf 'Warning: cache directory not found at %s\n' "$cache_root" >&2
fi

printf 'Reload complete. Start a new Codex session to observe refreshed skill instructions and hooks.\n'
