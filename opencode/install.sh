#!/usr/bin/env bash
#
# First-time setup: add the labflow plugin reference to opencode.json.
# The plugin loads agent, skills, and rules directly from the repo. Slash
# commands are symlinked into ~/.config/opencode/commands for native discovery.
#
# opencode loads config once at startup and does not hot-reload.
# After running this, quit and restart opencode.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
CONFIG_FILE="$CONFIG_DIR/opencode.json"
PLUGIN_ENTRY="file://$SRC/plugins/labflow.ts"
COMMAND_DIR="$CONFIG_DIR/commands"
IMAGEGEN_COMMAND_SRC="$SRC/commands/imagegen.md"
IMAGEGEN_COMMAND_DST="$COMMAND_DIR/imagegen.md"

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

mkdir -p "$COMMAND_DIR"
ln -sfn "$IMAGEGEN_COMMAND_SRC" "$IMAGEGEN_COMMAND_DST"

cat <<EOF

Done.

The labflow plugin is now registered. It injects:
  - labflow-rules.md (global cross-agent instructions)
  - labflow-develop agent (toggle with Tab in the TUI)
  - bundled ability skills
  - /imagegen command (symlinked to $IMAGEGEN_COMMAND_DST)

Quit and restart opencode for changes to take effect.
To disable, remove "$PLUGIN_ENTRY" from the "plugin" array,
or toggle the plugin in the opencode Plugin panel (space).
EOF
