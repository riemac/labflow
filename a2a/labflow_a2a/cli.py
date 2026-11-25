"""Command-line entrypoint for `labflow-a2a` (`daemon`, `mcp`, `wait-irq`, `version`)."""

from __future__ import annotations

import argparse
import sys

from . import VERSION
from .http_server import run_daemon
from .irq import run_wait_irq
from .mcp_server import run_mcp


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="labflow-a2a", description="Labflow Session-Addressable A2A 1.0 Service")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("daemon", help="Run the local A2A 1.0 workbench daemon (:7778 antigravity, :7779 codex)")

    p_mcp = sub.add_parser("mcp", help="Run stdio MCP server")
    p_mcp.add_argument("--self", dest="self_agent", choices=["antigravity", "codex"], required=True)

    p_irq = sub.add_parser("wait-irq", help="Block with 0% CPU until an inbound A2A message arrives for this GUI session")
    p_irq.add_argument("--agent", choices=["antigravity", "codex"], default="antigravity")
    p_irq.add_argument("--session", default="auto", help="Session UUID, title substring, or 'auto'")
    p_irq.add_argument("--timeout", type=float, default=0.0, help="Optional timeout in seconds (0 = wait indefinitely)")

    sub.add_parser("version", help="Print version")

    args = parser.parse_args(argv)
    if args.cmd == "version":
        print(f"labflow-a2a {VERSION}")
        return 0
    if args.cmd == "daemon":
        return run_daemon()
    if args.cmd == "mcp":
        return run_mcp(args.self_agent)
    if args.cmd == "wait-irq":
        return run_wait_irq(args.agent, args.session, args.timeout)
    return 2
