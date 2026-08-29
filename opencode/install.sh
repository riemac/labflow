#!/usr/bin/env bash
#
# Register labflow, manage its thin OpenCode bootstrap, and expose explicit
# encrypted configuration migration/device-authorization workflows.
#
# opencode loads config once at startup and does not hot-reload.
# After running this, quit and restart opencode.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${OPENCODE_CONFIG_DIR:-$HOME/.config/opencode}"
PLUGIN_ENTRY="file://$SRC/plugins/labflow.ts"
PACKAGE_FILE="$SRC/package.json"
CONFIG_MANAGER="$SRC/scripts/config-manager.mjs"
ACTION="bootstrap"
COMMAND_DIR="$CONFIG_DIR/commands"
LEGACY_IMAGEGEN_COMMAND_SRC="$SRC/commands/imagegen.md"
LEGACY_IMAGEGEN_COMMAND_DST="$COMMAND_DIR/imagegen.md"

case "${1:-}" in
  "") ACTION="bootstrap" ;;
  --migrate-config) ACTION="migrate" ;;
  --doctor) ACTION="doctor" ;;
  --init-age) ACTION="init-age" ;;
  --authorize-age-recipient)
    ACTION="authorize-age"
    [[ -n "${2:-}" ]] || { printf 'Missing age1... recipient.\n' >&2; exit 2; }
    ;;
  --help|-h)
    printf 'Usage: %s [--migrate-config|--doctor|--init-age|--authorize-age-recipient age1...]\n' "$0"
    exit 0
    ;;
  *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
esac

if [[ -f "$PACKAGE_FILE" && "$ACTION" == "bootstrap" ]]; then
  if command -v npm >/dev/null 2>&1; then
    printf 'Installing labflow opencode plugin dependencies...\n'
    npm --prefix "$SRC" install --omit=dev --ignore-scripts --loglevel=error >/dev/null
  else
    printf 'Warning: npm not found; custom tool dependencies may be missing.\n'
  fi
fi

if [[ "$ACTION" == "authorize-age" ]]; then
  node "$CONFIG_MANAGER" "$ACTION" "$2"
else
  node "$CONFIG_MANAGER" "$ACTION"
fi

if [[ "$ACTION" == "bootstrap" ]]; then
  missing_security_tools=()
  for command_name in sops age age-keygen; do
    command -v "$command_name" >/dev/null 2>&1 || missing_security_tools+=("$command_name")
  done
  if (( ${#missing_security_tools[@]} > 0 )); then
    printf 'Warning: encrypted config migration is unavailable; missing: %s\n' "${missing_security_tools[*]}"
    printf 'Install from the official releases, then run %s --init-age and %s --migrate-config.\n' "$0" "$0"
    printf '  https://github.com/getsops/sops/releases\n'
    printf '  https://github.com/FiloSottile/age/releases\n'
  fi
fi

if [[ "$ACTION" == "bootstrap" && -L "$LEGACY_IMAGEGEN_COMMAND_DST" ]]; then
  if [[ "$(readlink "$LEGACY_IMAGEGEN_COMMAND_DST")" == "$LEGACY_IMAGEGEN_COMMAND_SRC" ]]; then
    rm "$LEGACY_IMAGEGEN_COMMAND_DST"
    printf 'Removed legacy /imagegen command symlink from %s\n' "$LEGACY_IMAGEGEN_COMMAND_DST"
  else
    printf 'Leaving existing /imagegen command symlink untouched: %s\n' "$LEGACY_IMAGEGEN_COMMAND_DST"
  fi
elif [[ "$ACTION" == "bootstrap" && -e "$LEGACY_IMAGEGEN_COMMAND_DST" ]]; then
  printf 'Leaving existing /imagegen command file untouched: %s\n' "$LEGACY_IMAGEGEN_COMMAND_DST"
fi

if [[ "$ACTION" == "bootstrap" ]]; then
cat <<EOF

Done.

The labflow plugin is now registered. It injects:
  - labflow-rules.md (global cross-agent instructions)
  - labflow-develop agent (research dialogue, method design, explanation, and design scaffolding)
  - labflow-plan agent (read-only Codex-style planning, outputs <proposed_plan>)
  - labflow-paper agent (paper preparation, writing guidance, review, and submission readiness)
  - literature-worker subagent (bounded prior-art search and evidence artifacts)
  - learning-worker subagent (blind causal learning diagnosis and bounded probes)
  - bundled ability skills
  - opencode-pty startup plugin for primary-owned long-running sessions
  - imagegen generation/editing tool backed by opencode/scripts/imagegen.mjs

Toggle between agents with Tab. Quit and restart opencode for changes to take effect.
To disable, remove "$PLUGIN_ENTRY" from the "plugin" array,
or toggle the plugin in the opencode Plugin panel (space).
EOF
fi
