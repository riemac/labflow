"""Standard A2A 1.0 HTTP server (JSON-RPC 2.0 + HTTP+JSON REST + internal MCP helper API)."""

from __future__ import annotations

import http.server
import json
import signal
import socketserver
import threading
import urllib.parse
from typing import Any

from .config import AGENTS_CONFIG, BIND_HOST, VERSION
from .coordinator import TaskCoordinator
from .sessions import list_antigravity_sessions, list_codex_sessions


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], agent_name: str, coord: TaskCoordinator):
        self.agent_name = agent_name
        self.coord = coord
        super().__init__(server_address, A2ARequestHandler)


def build_agent_card(agent_name: str) -> dict[str, Any]:
    cfg = AGENTS_CONFIG[agent_name]
    url = cfg["url"]
    return {
        "name": cfg["name"],
        "description": cfg["description"],
        "version": VERSION,
        "supportedInterfaces": [
            {"url": url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"},
            {"url": url, "protocolBinding": "HTTP+JSON", "protocolVersion": "1.0"},
        ],
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [
            {
                "id": "workbench-session-messaging",
                "name": "Workbench Session Messaging",
                "description": "Address a specific GUI conversation via contextId or metadata.session (UUID, title, latest, or new).",
                "tags": ["a2a", "workbench", agent_name],
            }
        ],
        "provider": {"organization": "labflow", "url": "https://a2a-protocol.org/latest/"},
    }


class A2ARequestHandler(http.server.BaseHTTPRequestHandler):
    server: ThreadedHTTPServer

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_json(self, status: int, payload: Any) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("A2A-Version", "1.0")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        agent = self.server.agent_name
        coord = self.server.coord

        if path in ("/.well-known/agent-card.json", "/.well-known/agent.json", "/agent-card.json"):
            self._send_json(200, build_agent_card(agent))
            return

        if path == "/healthz":
            self._send_json(200, {"ok": True, "agent": agent, "version": VERSION})
            return

        if path in ("/tasks", "/v1/tasks"):
            ctx_id = (qs.get("contextId") or [""])[0]
            self._send_json(200, {"tasks": coord.list_tasks(agent=agent, context_id=ctx_id)})
            return

        if path.startswith("/tasks/") or path.startswith("/v1/tasks/"):
            tid = path.rstrip("/").split("/")[-1]
            try:
                self._send_json(200, coord.get_task(tid))
            except KeyError as e:
                self._send_json(404, {"error": {"code": 404, "message": str(e)}})
            return

        if path == "/internal/sessions":
            target = (qs.get("agent") or [agent])[0]
            q = (qs.get("query") or [""])[0]
            cwd = (qs.get("cwd") or [""])[0]
            limit = int((qs.get("limit") or ["20"])[0])
            sessions = (
                list_codex_sessions(query=q, cwd=cwd, limit=limit)
                if target == "codex"
                else list_antigravity_sessions(query=q, cwd=cwd, limit=limit)
            )
            for s in sessions:
                s["pending_inbox_count"] = coord.pending_count(target, s["session_id"])
            self._send_json(200, {"sessions": sessions})
            return

        if path == "/internal/inbox":
            target = (qs.get("agent") or [agent])[0]
            sid = (qs.get("session_id") or [""])[0]
            self._send_json(200, {"inbox": coord.get_inbox(target, sid)})
            return

        self._send_json(404, {"error": {"code": 404, "message": f"Unknown path {path}"}})

    def _handle_send_params(self, params: dict[str, Any]) -> dict[str, Any]:
        msg = params.get("message") or {}
        parts = msg.get("parts") or []
        text = "\n".join(p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p)
        meta = dict(params.get("metadata") or {})
        msg_meta = msg.get("metadata") or {}
        if isinstance(msg_meta, dict):
            meta.update(msg_meta)

        session_spec = str(meta.get("session") or msg.get("contextId") or "latest")
        cwd = str(meta.get("cwd") or "")
        sender = str(meta.get("from") or "a2a-client")
        cfg = params.get("configuration") or {}
        blocking = not (cfg.get("returnImmediately") is True or cfg.get("blocking") is False or meta.get("blocking") is False)
        timeout_sec = float(meta.get("timeout_sec", 90.0))

        return self.server.coord.create_and_dispatch(
            target_agent=self.server.agent_name,
            text=text,
            session_spec=session_spec,
            cwd=cwd,
            sender=sender,
            message_id=str(msg.get("messageId") or ""),
            extra_meta=meta,
            blocking=blocking,
            timeout_sec=timeout_sec,
        )

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        coord = self.server.coord

        try:
            body = self._read_json()
        except Exception as e:
            self._send_json(400, {"error": {"code": -32700, "message": f"Invalid JSON: {e}"}})
            return

        if path == "/internal/reply":
            try:
                task = coord.complete_task(
                    task_id=str(body["task_id"]),
                    reply_text=str(body["text"]),
                    responder=str(body.get("responder") or self.server.agent_name),
                )
                self._send_json(200, {"task": task})
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        if path in ("/message:send", "/v1/message:send"):
            try:
                self._send_json(200, {"task": self._handle_send_params(body)})
            except Exception as e:
                self._send_json(400, {"error": {"code": 400, "message": str(e)}})
            return

        if path.endswith(":cancel"):
            tid = path.split("/")[-1].removesuffix(":cancel")
            try:
                self._send_json(200, coord.cancel_task(tid))
            except KeyError as e:
                self._send_json(404, {"error": {"code": 404, "message": str(e)}})
            return

        if "method" in body:
            req_id = body.get("id")
            method = str(body.get("method") or "")
            params = body.get("params") or {}
            try:
                if method in ("SendMessage", "message/send"):
                    self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": {"task": self._handle_send_params(params)}})
                    return
                if method in ("GetTask", "tasks/get"):
                    tid = str(params.get("id") or str(params.get("name", "")).split("/")[-1])
                    self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": coord.get_task(tid)})
                    return
                if method in ("ListTasks", "tasks/list"):
                    ctx_id = str(params.get("contextId") or "")
                    self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": {"tasks": coord.list_tasks(agent=self.server.agent_name, context_id=ctx_id)}})
                    return
                if method in ("CancelTask", "tasks/cancel"):
                    tid = str(params.get("id") or str(params.get("name", "")).split("/")[-1])
                    self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "result": coord.cancel_task(tid)})
                    return
                self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})
            except KeyError as e:
                self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32001, "message": str(e)}})
            except Exception as e:
                self._send_json(200, {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": str(e)}})
            return

        self._send_json(404, {"error": {"code": 404, "message": f"Unsupported POST path {path}"}})


def run_daemon() -> int:
    """Run both always-on A2A 1.0 workbench endpoints (:7778 antigravity, :7779 codex)."""
    coord = TaskCoordinator()
    servers: list[ThreadedHTTPServer] = []
    for agent_name, cfg in AGENTS_CONFIG.items():
        srv = ThreadedHTTPServer((BIND_HOST, cfg["port"]), agent_name, coord)
        threading.Thread(target=srv.serve_forever, name=f"a2a-{agent_name}", daemon=True).start()
        servers.append(srv)
        print(f"[labflow-a2a] {agent_name} A2A 1.0 server listening on {cfg['url']}", flush=True)

    stop_ev = threading.Event()
    signal.signal(signal.SIGINT, lambda _s, _f: stop_ev.set())
    signal.signal(signal.SIGTERM, lambda _s, _f: stop_ev.set())
    stop_ev.wait()
    for srv in servers:
        srv.shutdown()
    return 0
