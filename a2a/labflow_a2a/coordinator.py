"""Thread-safe A2A 1.0 task store, session resolver, and wakeup dispatcher."""

from __future__ import annotations

import json
import pathlib
import subprocess
import threading
import time
import uuid
from typing import Any

from .codex_driver import create_new_codex_session, dispatch_to_codex
from .config import atomic_write_json, check_irq_armed, session_dir_for, state_root, utc_now_iso
from .sessions import resolve_existing_session


class TaskCoordinator:
    """Persists A2A 1.0 tasks, dispatches host wakeups, and signals blocking senders on completion."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._tasks_dir = state_root() / "tasks"
        self._tasks_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, dict[str, Any]] = {}
        self._load_existing()

    def _load_existing(self) -> None:
        for p in self._tasks_dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("id"):
                    self._tasks[data["id"]] = data
            except Exception:
                continue

    def _persist(self, task: dict[str, Any]) -> None:
        atomic_write_json(self._tasks_dir / f"{task['id']}.json", task)

    def _public_task(self, task: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in task.items() if not k.startswith("_")}

    def pending_count(self, agent: str, session_id: str) -> int:
        with self._cond:
            return sum(
                1
                for t in self._tasks.values()
                if t.get("_targetAgent") == agent
                and t.get("contextId") == session_id
                and t.get("status", {}).get("state") in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING")
            )

    def resolve_session(self, agent: str, session_spec: str, cwd: str = "") -> tuple[str, dict[str, Any]]:
        spec = (session_spec or "latest").strip()
        if agent == "codex" and spec.lower() == "new":
            new_id, new_proc = create_new_codex_session(cwd=cwd)
            return new_id, {
                "session_id": new_id,
                "title": "(new session)",
                "cwd": cwd or str(pathlib.Path.home()),
                "_new_proc": new_proc,
            }
        return resolve_existing_session(agent, spec, cwd=cwd)

    def create_and_dispatch(
        self,
        target_agent: str,
        text: str,
        session_spec: str = "",
        cwd: str = "",
        sender: str = "peer",
        message_id: str = "",
        extra_meta: dict[str, Any] | None = None,
        blocking: bool = True,
        timeout_sec: float = 90.0,
    ) -> dict[str, Any]:
        session_id, session_meta = self.resolve_session(target_agent, session_spec or "latest", cwd=cwd)
        task_id = str(uuid.uuid4())
        msg_id = message_id or str(uuid.uuid4())
        now = utc_now_iso()

        msg_metadata: dict[str, Any] = {
            "from": sender,
            "targetAgent": target_agent,
            "targetSessionId": session_id,
            "targetSessionTitle": session_meta.get("title") or "",
        }
        if extra_meta:
            msg_metadata.update(extra_meta)

        user_msg = {
            "messageId": msg_id,
            "contextId": session_id,
            "taskId": task_id,
            "role": "ROLE_USER",
            "parts": [{"text": text}],
            "metadata": msg_metadata,
        }

        task: dict[str, Any] = {
            "id": task_id,
            "contextId": session_id,
            "history": [user_msg],
            "status": {"state": "TASK_STATE_WORKING", "timestamp": now},
            "metadata": {
                "targetAgent": target_agent,
                "targetSessionId": session_id,
                "targetSessionTitle": session_meta.get("title") or "",
                "from": sender,
            },
            "_targetAgent": target_agent,
        }

        with self._cond:
            self._tasks[task_id] = task
            self._persist(task)

        delivery = self._wake_target(target_agent, session_id, session_meta, task_id, sender, text)
        with self._cond:
            task["metadata"]["delivery"] = delivery
            self._persist(task)

            if blocking and timeout_sec > 0:
                deadline = time.time() + timeout_sec
                while task["status"]["state"] in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING"):
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        break
                    self._cond.wait(timeout=remaining)

            return self._public_task(task)

    def _wake_target(
        self,
        target_agent: str,
        session_id: str,
        session_meta: dict[str, Any],
        task_id: str,
        sender: str,
        text: str,
    ) -> str:
        sdir = session_dir_for(target_agent, session_id)
        atomic_write_json(
            sdir / "irq.json",
            {"taskId": task_id, "contextId": session_id, "from": sender, "ts": utc_now_iso()},
        )

        if target_agent == "codex":
            return dispatch_to_codex(session_id, session_meta, task_id, sender, text)

        if target_agent == "antigravity":
            if check_irq_armed("antigravity", session_id):
                return "antigravity_irq_woken"
            title = session_meta.get("title") or session_id[:8]
            try:
                subprocess.run(
                    [
                        "notify-send",
                        f"A2A → Antigravity [{title}]",
                        f"来自 {sender} 的消息已进入会话 [{title}] 收件箱（task {task_id[:8]}）",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                )
            except Exception:
                pass
            return "queued_in_session_inbox_irq_unarmed"

        return "queued"

    def get_task(self, task_id: str) -> dict[str, Any]:
        with self._cond:
            t = self._tasks.get(task_id)
            if not t:
                raise KeyError(f"Task {task_id!r} not found")
            return self._public_task(t)

    def list_tasks(self, agent: str = "", context_id: str = "", limit: int = 50) -> list[dict[str, Any]]:
        with self._cond:
            items = list(self._tasks.values())
            if agent:
                items = [t for t in items if t.get("_targetAgent") == agent]
            if context_id:
                items = [t for t in items if t.get("contextId") == context_id]
            items.sort(key=lambda t: t.get("status", {}).get("timestamp") or "", reverse=True)
            return [self._public_task(t) for t in items[:limit]]

    def cancel_task(self, task_id: str) -> dict[str, Any]:
        with self._cond:
            t = self._tasks.get(task_id)
            if not t:
                raise KeyError(f"Task {task_id!r} not found")
            if t["status"]["state"] in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING"):
                t["status"] = {"state": "TASK_STATE_CANCELED", "timestamp": utc_now_iso()}
                self._persist(t)
                self._cond.notify_all()
            return self._public_task(t)

    def get_inbox(self, agent: str, session_id: str) -> list[dict[str, Any]]:
        with self._cond:
            pending: list[dict[str, Any]] = []
            for t in self._tasks.values():
                if t.get("_targetAgent") != agent:
                    continue
                if session_id and t.get("contextId") != session_id:
                    continue
                if t.get("status", {}).get("state") not in ("TASK_STATE_SUBMITTED", "TASK_STATE_WORKING"):
                    continue
                first_msg = (t.get("history") or [{}])[0]
                text = "".join(p.get("text", "") for p in first_msg.get("parts", []) if isinstance(p, dict))
                pending.append({
                    "task_id": t["id"],
                    "session_id": t["contextId"],
                    "from": t.get("metadata", {}).get("from", "peer"),
                    "text": text,
                    "timestamp": t.get("status", {}).get("timestamp", ""),
                })
            pending.sort(key=lambda x: x.get("timestamp") or "")
            return pending

    def complete_task(self, task_id: str, reply_text: str, responder: str = "") -> dict[str, Any]:
        with self._cond:
            t = self._tasks.get(task_id)
            if not t:
                raise KeyError(f"Task {task_id!r} not found")
            now = utc_now_iso()
            reply_msg: dict[str, Any] = {
                "messageId": str(uuid.uuid4()),
                "contextId": t["contextId"],
                "taskId": task_id,
                "role": "ROLE_AGENT",
                "parts": [{"text": reply_text}],
            }
            if responder:
                reply_msg["metadata"] = {"responder": responder}
            t.setdefault("history", []).append(reply_msg)
            t["artifacts"] = [
                {
                    "artifactId": str(uuid.uuid4()),
                    "name": "reply",
                    "parts": [{"text": reply_text}],
                }
            ]
            t["status"] = {"state": "TASK_STATE_COMPLETED", "message": reply_msg, "timestamp": now}
            self._persist(t)
            self._cond.notify_all()
            return self._public_task(t)
