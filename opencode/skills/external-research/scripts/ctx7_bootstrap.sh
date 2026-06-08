#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ctx7_bootstrap.sh status [--json]
  ctx7_bootstrap.sh ensure --yes

Checks or installs the ctx7 CLI stack used by external-research.
EOF
}

json_bool() {
  if [[ "$1" == "true" ]]; then
    printf "true"
  else
    printf "false"
  fi
}

json_string() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '"%s"' "$value"
}

status_json() {
  local ctx7_path npm_path ctx7_version skills_root find_docs context7_cli
  ctx7_path="$(command -v ctx7 || true)"
  npm_path="$(command -v npm || true)"
  ctx7_version=""
  if [[ -n "$ctx7_path" ]]; then
    ctx7_version="$(ctx7 --version 2>/dev/null || true)"
  fi
  skills_root="${HOME}/.agents/skills"
  [[ -f "${skills_root}/find-docs/SKILL.md" ]] && find_docs=true || find_docs=false
  [[ -f "${skills_root}/context7-cli/SKILL.md" ]] && context7_cli=true || context7_cli=false

  cat <<EOF
{
  "ctx7": {
    "present": $(json_bool "$([[ -n "$ctx7_path" ]] && echo true || echo false)"),
    "path": $(json_string "${ctx7_path:-}"),
    "version": $(json_string "${ctx7_version:-}")
  },
  "npm": {
    "present": $(json_bool "$([[ -n "$npm_path" ]] && echo true || echo false)"),
    "path": $(json_string "${npm_path:-}")
  },
  "skills": {
    "find-docs": ${find_docs},
    "context7-cli": ${context7_cli}
  }
}
EOF
}

status_text() {
  if command -v ctx7 >/dev/null 2>&1; then
    printf 'ctx7: ok (%s)\n' "$(ctx7 --version 2>/dev/null || true)"
  else
    printf 'ctx7: missing\n'
  fi
  [[ -f "${HOME}/.agents/skills/find-docs/SKILL.md" ]] && printf 'find-docs skill: ok\n' || printf 'find-docs skill: missing\n'
  [[ -f "${HOME}/.agents/skills/context7-cli/SKILL.md" ]] && printf 'context7-cli skill: ok\n' || printf 'context7-cli skill: missing\n'
}

run_with_proxy_retry() {
  if "$@"; then
    return 0
  fi
  if [[ "${NODE_OPTIONS:-}" == *"--use-env-proxy"* ]]; then
    return 1
  fi
  NODE_OPTIONS="${NODE_OPTIONS:-} --use-env-proxy" "$@"
}

ensure() {
  local yes="${1:-}"
  if [[ "$yes" != "--yes" ]]; then
    printf 'Refusing to install without --yes.\n' >&2
    return 2
  fi

  if ! command -v ctx7 >/dev/null 2>&1; then
    command -v npm >/dev/null 2>&1 || {
      printf 'npm is required to install ctx7, but npm was not found.\n' >&2
      return 1
    }
    run_with_proxy_retry npm install -g ctx7@latest
  fi

  run_with_proxy_retry ctx7 setup --cli --universal -y
  run_with_proxy_retry ctx7 skills install /upstash/context7 context7-cli --global --universal -y
  status_json
}

main() {
  local command="${1:-}"
  case "$command" in
    status)
      if [[ "${2:-}" == "--json" ]]; then
        status_json
      else
        status_text
      fi
      ;;
    ensure)
      ensure "${2:-}"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      usage >&2
      return 2
      ;;
  esac
}

main "$@"
