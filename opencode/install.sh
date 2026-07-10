#!/usr/bin/env bash
#
# First-time setup: add the labflow plugin reference to opencode.json.
# The plugin loads agents, skills, rules, and custom tools directly from the repo.
#
# opencode loads config once at startup and does not hot-reload.
# After running this, quit and restart opencode.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
CONFIG_FILE="$CONFIG_DIR/opencode.json"
PLUGIN_ENTRY="file://$SRC/plugins/labflow.ts"
PACKAGE_FILE="$SRC/package.json"
COMMAND_DIR="$CONFIG_DIR/commands"
LEGACY_IMAGEGEN_COMMAND_SRC="$SRC/commands/imagegen.md"
LEGACY_IMAGEGEN_COMMAND_DST="$COMMAND_DIR/imagegen.md"

if [[ -f "$PACKAGE_FILE" ]]; then
  if command -v npm >/dev/null 2>&1; then
    printf 'Installing labflow opencode plugin dependencies...\n'
    npm --prefix "$SRC" install --omit=dev --ignore-scripts --loglevel=error >/dev/null
  else
    printf 'Warning: npm not found; custom tool dependencies may be missing.\n'
  fi
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
  printf 'No config file found at %s. Creating minimal config.\n' "$CONFIG_FILE"
  cat > "$CONFIG_FILE" <<EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "plugin": ["$PLUGIN_ENTRY"]
}
EOF
  printf 'Config created. Add your provider/model config before starting.\n'
else
  if grep -qF "$PLUGIN_ENTRY" "$CONFIG_FILE" 2>/dev/null; then
    printf 'Plugin entry already present in %s\n' "$CONFIG_FILE"
  else
    printf 'Adding plugin entry to %s...\n' "$CONFIG_FILE"
    python3 -c "
import json, sys
with open('$CONFIG_FILE') as f:
    cfg = json.load(f)
plugin = cfg.get('plugin', [])
if isinstance(plugin, list):
    plugin.append('$PLUGIN_ENTRY')
    cfg['plugin'] = plugin
else:
    cfg['plugin'] = ['$PLUGIN_ENTRY']
with open('$CONFIG_FILE', 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
" && echo "Added."
  fi
fi

if [[ -L "$LEGACY_IMAGEGEN_COMMAND_DST" ]]; then
  if [[ "$(readlink "$LEGACY_IMAGEGEN_COMMAND_DST")" == "$LEGACY_IMAGEGEN_COMMAND_SRC" ]]; then
    rm "$LEGACY_IMAGEGEN_COMMAND_DST"
    printf 'Removed legacy /imagegen command symlink from %s\n' "$LEGACY_IMAGEGEN_COMMAND_DST"
  else
    printf 'Leaving existing /imagegen command symlink untouched: %s\n' "$LEGACY_IMAGEGEN_COMMAND_DST"
  fi
elif [[ -e "$LEGACY_IMAGEGEN_COMMAND_DST" ]]; then
  printf 'Leaving existing /imagegen command file untouched: %s\n' "$LEGACY_IMAGEGEN_COMMAND_DST"
fi

cat <<EOF

Done.

The labflow plugin is now registered. It injects:
  - labflow-rules.md (global cross-agent instructions)
  - labflow-develop agent (R&D discussion + design scaffolding)
  - labflow-plan agent (read-only Codex-style planning, outputs <proposed_plan>)
  - labflow-paper agent (paper preparation, writing guidance, review, and submission readiness)
  - literature-worker subagent (bounded prior-art search and evidence artifacts)
  - bundled ability skills
  - imagegen custom tool backed by opencode/scripts/imagegen.mjs

Toggle between agents with Tab. Quit and restart opencode for changes to take effect.
To disable, remove "$PLUGIN_ENTRY" from the "plugin" array,
or toggle the plugin in the opencode Plugin panel (space).
EOF
