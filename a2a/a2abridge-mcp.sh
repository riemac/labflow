#!/usr/bin/env bash
# Single-threaded MCP launcher wrapper for a2abridge on Linux.
#
# Why this exists:
# Upstream a2abridge (v4.0.3, internal/cli/pdeathsig_linux.go) calls
# prctl(PR_SET_PDEATHSIG, SIGTERM). On Linux, PR_SET_PDEATHSIG fires when the
# spawning OS thread (not the parent process) exits. Multi-threaded MCP hosts
# such as Codex Desktop / app-server (Rust/Tokio) spawn MCP servers from a
# worker thread pool and retire idle threads after ~40s, causing the kernel to
# kill a2abridge prematurely ("Transport closed").
#
# Keeping this single-threaded shell process as a2abridge's direct parent
# (intentionally avoiding tail-call `exec`) prevents false SIGTERM while still
# inheriting stdin/stdout directly so host shutdown / stdin EOF exits cleanly.

set -euo pipefail

BIN="${A2ABRIDGE_BIN:-${HOME}/.local/bin/a2abridge}"
status=0
"$BIN" "$@" || status=$?
exit "$status"
