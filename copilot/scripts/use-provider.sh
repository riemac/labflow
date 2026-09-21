#!/usr/bin/env bash

# Source this file to set environment variables for GitHub Copilot CLI BYOK:
#   source copilot/scripts/use-provider.sh routin-plan gpt-5.6-terra
# Or:
#   eval "$(copilot/scripts/use-provider.sh routin-plan gpt-5.6-terra)"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
eval "$(node "$SCRIPT_DIR/sync-providers.mjs" --env "$@")"
