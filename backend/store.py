"""SQLite history for completed analyses. The crew itself is unchanged."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from pathlib import Path

from backend.config import PROJECT_ROOT

_DB_PATH = PROJECT_ROOT / "data" / "estetik.sqlite"
_LOCK = threading.Lock()


def save_completed_analysis(
    *,
    original_request: str,
    result: dict,
    started_at: str,
    completed_at: str,
) -> dict:
    record_id = str(uuid.uuid4())
    sources = result.get("knowledge_sources") or []
    escalation = bool(result.get("escalation_required"))
    record = {
        "id": record_id,
        "original_request": original_request,
        "request_type": result.get("request_type") or "Unknown",
        "category": result.get("category") or "Unspecified",
        "priority": result.get("priority") or "Medium",
        "verified_information": list(result.get("verified_information") or []),
        "missing_information": list(result.get("missing_information") or []),
        "recommended_actions": list(result.get("recommended_actions") or []),
        "escalation_required": escalation,
        "reason": result.get("reason") or "",
        "knowledge_sources": sources,
        "anythingllm_error": bool(result.get("anythingllm_error")),
        "created_at": completed_at,
    }
    events = [
        ("request_received", started_at),
        ("analysis_completed", completed_at),
    ]
    if sources and not record["anythingllm_error"]:
        events.append(("knowledge_sources_used", completed_at))
    if escalation:
        events.append(("escalation_created", completed_at))

    with _LOCK:
        connection = _connect()
        try:
            connection.execute(
                """
                INSERT INTO analyses (
                    id, original_request, request_type, category, priority,
                    verified_information, missing_information, recommended_actions,
                    escalation_required, reason, knowledge_sources, anythingllm_error, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["id"],
                    record["original_request"],
                    record["request_type"],
                    record["category"],
                    record["priority"],
                    json.dumps(record["verified_information"], ensure_ascii=False),
                    json.dumps(record["missing_information"], ensure_ascii=False),
                    json.dumps(record["recommended_actions"], ensure_ascii=False),
                    1 if escalation else 0,
                    record["reason"],
                    json.dumps(sources, ensure_ascii=False),
                    1 if record["anythingllm_error"] else 0,
                    completed_at,
                ),
            )
            for sequence, (event_type, timestamp) in enumerate(events):
                connection.execute(
                    """
                    INSERT INTO activity (id, event_type, request_id, request_preview, created_at, sequence)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        event_type,
                        record_id,
                        original_request,
                        timestamp,
                        sequence,
                    ),
                )
            connection.commit()
        finally:
            connection.close()
    return record


def list_requests() -> list[dict]:
    with _LOCK:
        connection = _connect()
        try:
            rows = connection.execute(
                """
                SELECT id, original_request, request_type, category, priority,
                       escalation_required, anythingllm_error, created_at
                FROM analyses
                ORDER BY created_at DESC
                """
            ).fetchall()
        finally:
            connection.close()
    return [_summary(row) for row in rows]


def get_request(request_id: str) -> dict | None:
    with _LOCK:
        connection = _connect()
        try:
            row = connection.execute("SELECT * FROM analyses WHERE id = ?", (request_id,)).fetchone()
        finally:
            connection.close()
    if row is None:
        return None
    return _full(row)


def list_escalations() -> dict:
    records = [item for item in _full_rows() if item["escalation_required"]]
    high = sum(1 for item in records if item["priority"].casefold() == "high")
    medium = sum(1 for item in records if item["priority"].casefold() == "medium")
    return {
        "open_count": len(records),
        "high_count": high,
        "medium_count": medium,
        "items": records,
    }


def list_activity() -> list[dict]:
    with _LOCK:
        connection = _connect()
        try:
            rows = connection.execute(
                """
                SELECT id, event_type, request_id, request_preview, created_at
                FROM activity
                ORDER BY created_at DESC, sequence DESC
                """
            ).fetchall()
        finally:
            connection.close()
    return [
        {
            "id": row["id"],
            "event_type": row["event_type"],
            "request_id": row["request_id"],
            "request_preview": row["request_preview"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def source_usage() -> dict[str, dict]:
    usage: dict[str, dict] = {}
    for record in _full_rows():
        for source in record["knowledge_sources"]:
            if not isinstance(source, dict):
                continue
            title = str(source.get("title") or "").strip()
            if not title:
                continue
            key = _canonical_title(title).casefold()
            current = usage.get(key)
            if current is None or record["created_at"] >= current["last_used_at"]:
                usage[key] = {
                    "title": _canonical_title(title),
                    "use_count": 0 if current is None else current["use_count"],
                    "last_used_at": record["created_at"],
                    "last_request_id": record["id"],
                    "last_request_preview": record["original_request"],
                }
            usage[key]["use_count"] += 1
    return usage


def _full_rows() -> list[dict]:
    with _LOCK:
        connection = _connect()
        try:
            rows = connection.execute("SELECT * FROM analyses ORDER BY created_at DESC").fetchall()
        finally:
            connection.close()
    return [_full(row) for row in rows]


def _connect() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(_DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            original_request TEXT NOT NULL,
            request_type TEXT NOT NULL,
            category TEXT NOT NULL,
            priority TEXT NOT NULL,
            verified_information TEXT NOT NULL,
            missing_information TEXT NOT NULL,
            recommended_actions TEXT NOT NULL,
            escalation_required INTEGER NOT NULL,
            reason TEXT NOT NULL,
            knowledge_sources TEXT NOT NULL,
            anythingllm_error INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS activity (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            request_id TEXT NOT NULL,
            request_preview TEXT NOT NULL,
            created_at TEXT NOT NULL,
            sequence INTEGER NOT NULL
        )
        """
    )
    return connection


def _summary(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "original_request": row["original_request"],
        "request_type": row["request_type"],
        "category": row["category"],
        "priority": row["priority"],
        "escalation_required": bool(row["escalation_required"]),
        "anythingllm_error": bool(row["anythingllm_error"]),
        "created_at": row["created_at"],
    }


def _full(row: sqlite3.Row) -> dict:
    item = _summary(row)
    item.update(
        {
            "verified_information": json.loads(row["verified_information"]),
            "missing_information": json.loads(row["missing_information"]),
            "recommended_actions": json.loads(row["recommended_actions"]),
            "reason": row["reason"],
            "knowledge_sources": json.loads(row["knowledge_sources"]),
        }
    )
    return item


def _canonical_title(title: str) -> str:
    name = title.replace("\\", "/").rsplit("/", 1)[-1]
    if name.lower().endswith(".json"):
        stem = name[:-5]
        marker = stem.rfind(".pdf-")
        if marker != -1:
            return stem[: marker + 4]
    return name
