"""Stdio MCP server exposing 6 deterministic A2A 1.0 workbench primitives."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

from .config import AGENTS_CONFIG, VERSION
from .sessions import detect_self_session_id, list_antigravity_sessions, list_codex_sessions


def http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: float = 120.0) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "A2A-Version": "1.0"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {e.code} from {url}: {raw}") from e


MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "a2a_list_agents",
        "description": "List available A2A 1.0 workbench agents (antigravity, codex) and check their live health.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "a2a_list_sessions",
        "description": "List GUI conversations/sessions in `codex` or `antigravity` with their session_id (contextId), title, cwd, IRQ status, and pending inbox count.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": ["codex", "antigravity", "all"], "default": "all"},
                "query": {"type": "string", "description": "Optional substring filter on session title, UUID, or cwd."},
                "cwd": {"type": "string", "description": "Optional working directory filter."},
                "limit": {"type": "integer", "default": 15},
            },
        },
    },
    {
        "name": "a2a_send",
        "description": "Send a natural-language A2A 1.0 message to a specific session in `codex` or `antigravity` (or any A2A URL). For `codex`, automatically wakes open GUI chats or revives cold chats (pass session='new' to create a fresh chat). Never silently falls back to CLI for Antigravity App sessions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "description": "'codex', 'antigravity', or a full http(s):// A2A agent URL."},
                "session": {
                    "type": "string",
                    "description": "Target session UUID (contextId), conversation title substring, 'latest' (default), or 'new' (Codex only).",
                    "default": "latest",
                },
                "text": {"type": "string", "description": "Natural-language message body to send."},
                "cwd": {"type": "string", "description": "Working directory filter (or directory for session='new')."},
                "blocking": {"type": "boolean", "default": True, "description": "Wait for the target session's reply."},
                "timeout_sec": {"type": "number", "default": 90, "description": "Max seconds to wait before returning WORKING task_id."},
            },
            "required": ["agent", "text"],
        },
    },
    {
        "name": "a2a_get_task",
        "description": "Fetch current A2A 1.0 Task state and reply artifacts by task_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "default": "codex", "description": "'codex', 'antigravity', or peer URL."},
                "task_id": {"type": "string"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "a2a_inbox",
        "description": "Read pending inbound A2A tasks addressed to this session (isolated per session_id so tabs never mix).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session": {
                    "type": "string",
                    "default": "auto",
                    "description": "'auto' (detect current GUI session), 'all' (all pending tasks for this app), or an explicit session UUID/title.",
                }
            },
        },
    },
    {
        "name": "a2a_reply",
        "description": "Complete an inbound A2A task with your reply text, immediately unblocking the waiting sender.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "text": {"type": "string", "description": "Reply content to return as an A2A Artifact."},
            },
            "required": ["task_id", "text"],
        },
    },
]


def resolve_agent_url(agent_or_url: str) -> str:
    key = agent_or_url.strip().lower()
    if key in AGENTS_CONFIG:
        return AGENTS_CONFIG[key]["url"]
    if agent_or_url.startswith("http://") or agent_or_url.startswith("https://"):
        return agent_or_url.rstrip("/")
    raise ValueError(f"Unknown agent {agent_or_url!r}; expected 'codex', 'antigravity', or http(s):// URL")


def handle_mcp_tool(self_agent: str, name: str, args: dict[str, Any]) -> Any:
    control_url = AGENTS_CONFIG["antigravity"]["url"]

    if name == "a2a_list_agents":
        out = []
        for ag_name, cfg in AGENTS_CONFIG.items():
            try:
                online = bool(http_json("GET", f"{cfg['url']}/healthz", timeout=3.0).get("ok"))
            except Exception:
                online = False
            out.append({"agent": ag_name, "url": cfg["url"], "online": online, "self": ag_name == self_agent})
        return out

    if name == "a2a_list_sessions":
        target = str(args.get("agent") or "all").lower()
        targets = ["codex", "antigravity"] if target == "all" else [target]
        qs_base = {
            "query": str(args.get("query") or ""),
            "cwd": str(args.get("cwd") or ""),
            "limit": str(int(args.get("limit") or 15)),
        }
        combined: list[dict[str, Any]] = []
        for t in targets:
            qs = urllib.parse.urlencode({**qs_base, "agent": t})
            combined.extend(http_json("GET", f"{control_url}/internal/sessions?{qs}", timeout=8.0).get("sessions", []))
        return combined

    if name == "a2a_send":
        url = resolve_agent_url(str(args["agent"]))
        session = str(args.get("session") or "latest")
        text = str(args["text"])
        cwd = str(args.get("cwd") or "")
        blocking = bool(args.get("blocking", True))
        timeout_sec = float(args.get("timeout_sec", 90.0))
        self_sid = detect_self_session_id(self_agent)
        sender_label = f"{self_agent}:{self_sid[:8]}" if self_sid else self_agent

        rpc_req = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "contextId": session,
                    "role": "ROLE_USER",
                    "parts": [{"text": text}],
                    "metadata": {
                        "from": sender_label,
                        "fromAgent": self_agent,
                        "fromSessionId": self_sid,
                        "session": session,
                        "cwd": cwd,
                        "blocking": blocking,
                        "timeout_sec": timeout_sec,
                    },
                },
                "configuration": {"returnImmediately": not blocking},
            },
        }
        resp = http_json("POST", f"{url}/", payload=rpc_req, timeout=max(10.0, timeout_sec + 15.0))
        if "error" in resp:
            raise RuntimeError(resp["error"].get("message") or str(resp["error"]))
        return resp.get("result", {}).get("task", resp.get("result"))

    if name == "a2a_get_task":
        url = resolve_agent_url(str(args.get("agent") or "codex"))
        resp = http_json(
            "POST",
            f"{url}/",
            payload={"jsonrpc": "2.0", "id": 1, "method": "GetTask", "params": {"id": str(args["task_id"])}},
            timeout=10.0,
        )
        if "error" in resp:
            raise RuntimeError(resp["error"].get("message") or str(resp["error"]))
        return resp.get("result")

    if name == "a2a_inbox":
        sess_arg = str(args.get("session") or "auto").strip()
        if sess_arg.lower() == "all":
            sid = ""
        elif sess_arg.lower() in ("auto", ""):
            sid = detect_self_session_id(self_agent)
        else:
            sessions = (
                list_codex_sessions(query=sess_arg, limit=5)
                if self_agent == "codex"
                else list_antigravity_sessions(query=sess_arg, limit=5)
            )
            sid = sessions[0]["session_id"] if sessions else sess_arg
        qs = urllib.parse.urlencode({"agent": self_agent, "session_id": sid})
        res = http_json("GET", f"{control_url}/internal/inbox?{qs}", timeout=8.0)
        return {"self_agent": self_agent, "session_id": sid or "(all)", "inbox": res.get("inbox", [])}

    if name == "a2a_reply":
        res = http_json(
            "POST",
            f"{control_url}/internal/reply",
            payload={"task_id": str(args["task_id"]), "text": str(args["text"]), "responder": self_agent},
            timeout=10.0,
        )
        if "error" in res:
            raise RuntimeError(str(res["error"]))
        return res.get("task")

    raise ValueError(f"Unknown MCP tool: {name}")


def run_mcp(self_agent: str) -> int:
    """Run JSON-RPC 2.0 MCP server over stdio."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            continue

        req_id = msg.get("id")
        if req_id is None:
            continue
        method = msg.get("method", "")

        if method == "initialize":
            client_proto = (msg.get("params") or {}).get("protocolVersion") or "2024-11-05"
            reply = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": client_proto,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "labflow-a2a", "version": VERSION},
                },
            }
        elif method == "ping":
            reply = {"jsonrpc": "2.0", "id": req_id, "result": {}}
        elif method == "tools/list":
            reply = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
        elif method == "tools/call":
            params = msg.get("params") or {}
            try:
                out = handle_mcp_tool(self_agent, str(params.get("name") or ""), params.get("arguments") or {})
                text_out = out if isinstance(out, str) else json.dumps(out, ensure_ascii=False, indent=2)
                reply = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": text_out}], "isError": False},
                }
            except Exception as e:
                reply = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True},
                }
        else:
            reply = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}

        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0
