"""Read-only session indexers and deterministic session-spec resolution for Codex and Antigravity."""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sqlite3
import urllib.parse
import uuid
from typing import Any

from .config import check_irq_armed


def list_codex_sessions(
    query: str = "",
    cwd: str = "",
    limit: int = 20,
    include_exec: bool = False,
) -> list[dict[str, Any]]:
    """Read-only scan of ~/.codex/session_index.jsonl and recent rollout headers."""
    home = pathlib.Path.home()
    codex_home = pathlib.Path(os.environ.get("CODEX_HOME", str(home / ".codex")))
    index_map: dict[str, dict[str, Any]] = {}

    sidx = codex_home / "session_index.jsonl"
    if sidx.exists():
        try:
            for line in sidx.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    sid = item.get("id")
                    if sid:
                        index_map[sid] = {
                            "session_id": sid,
                            "title": item.get("thread_name") or "",
                            "updated_at": item.get("updated_at") or "",
                            "cwd": "",
                            "source": "vscode",
                            "originator": "Codex Desktop",
                        }
                except Exception:
                    continue
        except OSError:
            pass

    # Enrich with cwd/source/mtime from newest 250 rollout files (<30ms latency).
    sessions_root = codex_home / "sessions"
    if sessions_root.exists():
        rollouts: list[tuple[float, pathlib.Path]] = []
        for p in sessions_root.rglob("*.jsonl"):
            try:
                rollouts.append((p.stat().st_mtime, p))
            except OSError:
                continue
        rollouts.sort(key=lambda x: x[0], reverse=True)

        for mtime, path in rollouts[:250]:
            try:
                with path.open("r", encoding="utf-8", errors="ignore") as f:
                    first = f.readline()
                meta = json.loads(first).get("payload", {})
                sid = meta.get("id") or meta.get("session_id")
                if not sid:
                    continue
                iso_mtime = dt.datetime.fromtimestamp(mtime, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                rec = index_map.get(sid, {"session_id": sid, "title": "", "updated_at": iso_mtime})
                if not rec.get("updated_at") or iso_mtime > rec["updated_at"]:
                    rec["updated_at"] = iso_mtime
                rec["cwd"] = meta.get("cwd") or rec.get("cwd") or ""
                rec["source"] = meta.get("source") or rec.get("source") or ""
                rec["originator"] = meta.get("originator") or rec.get("originator") or ""
                index_map[sid] = rec
            except Exception:
                continue

    target_cwd = os.path.realpath(cwd) if cwd else ""
    q = query.strip().lower()
    results: list[dict[str, Any]] = []

    for rec in index_map.values():
        if not include_exec and rec.get("source") == "exec" and q != rec["session_id"].lower():
            continue
        if target_cwd:
            rcwd = rec.get("cwd") or ""
            if not rcwd or os.path.realpath(rcwd) != target_cwd:
                continue
        if q:
            hay = f"{rec['session_id']} {rec.get('title', '')} {rec.get('cwd', '')}".lower()
            if q not in hay:
                continue
        rec["agent"] = "codex"
        results.append(rec)

    results.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return results[: max(1, limit)]


def list_antigravity_sessions(query: str = "", cwd: str = "", limit: int = 20) -> list[dict[str, Any]]:
    """Read-only scan of ~/.gemini/antigravity/conversation_summaries.db for App conversations."""
    db_path = pathlib.Path.home() / ".gemini" / "antigravity" / "conversation_summaries.db"
    if not db_path.exists():
        return []

    target_cwd = os.path.realpath(cwd) if cwd else ""
    q = query.strip().lower()
    results: list[dict[str, Any]] = []

    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=3.0)
    try:
        cur = con.cursor()
        rows = cur.execute(
            """
            SELECT conversation_id, title, preview, last_modified_time, workspace_uris, status, source
            FROM conversation_summaries
            WHERE killed = 0
            ORDER BY last_modified_time DESC
            LIMIT 200
            """
        ).fetchall()
    finally:
        con.close()

    for cid, title, preview, mod_time, ws_raw, status, source in rows:
        # Strictly target Antigravity App sessions (never CLI clones).
        if source == "CORTEX_TRAJECTORY_SOURCE_CLI" and q != (cid or "").lower():
            continue
        workspaces: list[str] = []
        if ws_raw:
            try:
                parsed_ws = json.loads(ws_raw)
                if isinstance(parsed_ws, list):
                    for u in parsed_ws:
                        if isinstance(u, str):
                            workspaces.append(urllib.parse.unquote(u.removeprefix("file://")))
            except Exception:
                pass
        primary_cwd = workspaces[0] if workspaces else ""
        if target_cwd and not any(os.path.realpath(w) == target_cwd for w in workspaces if w):
            continue
        display_title = (title or preview or "").strip()
        if q:
            hay = f"{cid} {display_title} {primary_cwd}".lower()
            if q not in hay:
                continue
        results.append({
            "agent": "antigravity",
            "session_id": cid,
            "title": display_title,
            "cwd": primary_cwd,
            "status": status or "",
            "updated_at": mod_time or "",
            "irq_armed": check_irq_armed("antigravity", cid),
        })
        if len(results) >= max(1, limit):
            break

    return results


def detect_self_session_id(self_agent: str) -> str:
    """Auto-detect the active session ID for the calling harness when `session='auto'`."""
    meta_raw = os.environ.get("ANTIGRAVITY_SOURCE_METADATA")
    if meta_raw:
        try:
            cid = json.loads(meta_raw).get("tool", {}).get("conversationId")
            if cid:
                return str(cid)
        except Exception:
            pass

    if self_agent == "antigravity":
        sessions = list_antigravity_sessions(limit=20)
        running = [s for s in sessions if s.get("status") == "CASCADE_RUN_STATUS_RUNNING"]
        if running:
            return running[0]["session_id"]
        return sessions[0]["session_id"] if sessions else ""

    if self_agent == "codex":
        scoped = list_codex_sessions(cwd=os.getcwd(), limit=10)
        if scoped:
            return scoped[0]["session_id"]
        any_sess = list_codex_sessions(limit=5)
        return any_sess[0]["session_id"] if any_sess else ""

    return ""


def resolve_existing_session(agent: str, session_spec: str, cwd: str = "") -> tuple[str, dict[str, Any]]:
    """Deterministically resolve UUID, title substring, or 'latest' for an existing session."""
    spec = (session_spec or "latest").strip()

    if agent == "codex":
        sessions = list_codex_sessions(limit=200, include_exec=True)
        for s in sessions:
            if s["session_id"].lower() == spec.lower():
                return s["session_id"], s
        try:
            uuid.UUID(spec)
            return spec, {"session_id": spec, "title": "", "cwd": cwd}
        except ValueError:
            pass

        workbench_sessions = [s for s in sessions if s.get("source") != "exec"]
        if cwd:
            real_cwd = os.path.realpath(cwd)
            scoped = [s for s in workbench_sessions if s.get("cwd") and os.path.realpath(s["cwd"]) == real_cwd]
        else:
            scoped = workbench_sessions

        if spec.lower() in ("latest", "auto", ""):
            if not scoped:
                raise ValueError(f"No existing Codex workbench session found (cwd={cwd!r}). Pass session='new' to create one.")
            return scoped[0]["session_id"], scoped[0]

        exact = [s for s in scoped if (s.get("title") or "").strip().lower() == spec.lower()]
        if exact:
            return exact[0]["session_id"], exact[0]
        sub = [s for s in scoped if spec.lower() in f"{s.get('title', '')} {s.get('cwd', '')}".lower()]
        if sub:
            return sub[0]["session_id"], sub[0]

        sample = ", ".join(f"{s['session_id'][:8]}({s.get('title') or s.get('cwd')})" for s in workbench_sessions[:5])
        raise ValueError(f"Codex session {spec!r} not found. Recent sessions: [{sample}]")

    if agent == "antigravity":
        if spec.lower() == "new":
            raise ValueError(
                "Antigravity App does not expose an API to open a new GUI tab externally; "
                "open a tab in Antigravity App first or target an existing session ID/title."
            )
        sessions = list_antigravity_sessions(limit=200)
        for s in sessions:
            if s["session_id"].lower() == spec.lower():
                return s["session_id"], s
        try:
            uuid.UUID(spec)
            return spec, {"session_id": spec, "title": "", "cwd": cwd}
        except ValueError:
            pass

        scoped = sessions
        if cwd:
            real_cwd = os.path.realpath(cwd)
            scoped = [s for s in sessions if s.get("cwd") and os.path.realpath(s["cwd"]) == real_cwd]

        if spec.lower() in ("latest", "auto", ""):
            armed = [s for s in scoped if s.get("irq_armed")]
            chosen = armed[0] if armed else (scoped[0] if scoped else None)
            if not chosen:
                raise ValueError("No Antigravity App session found.")
            return chosen["session_id"], chosen

        exact = [s for s in scoped if (s.get("title") or "").strip().lower() == spec.lower()]
        if exact:
            return exact[0]["session_id"], exact[0]
        sub = [s for s in scoped if spec.lower() in (s.get("title") or "").lower()]
        if sub:
            return sub[0]["session_id"], sub[0]

        sample = ", ".join(f"{s['session_id'][:8]}({s.get('title')})" for s in sessions[:5])
        raise ValueError(f"Antigravity session {spec!r} not found. Recent App sessions: [{sample}]")

    raise ValueError(f"Unknown local agent: {agent!r}")
