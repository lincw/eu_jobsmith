"""簡報評估與儲存。"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.store import db


def _label(label: str, presentation_label: str) -> str:
    if label.strip():
        return label.strip()[:200]
    if presentation_label.strip():
        return f"{presentation_label.strip()} 簡報提問"
    return "未命名簡報提問"


def save_check(
    label: str,
    presentation_label: str,
    assessment: dict,
) -> int:
    conn = db.get_conn()
    with db.LOCK:
        cur = conn.execute(
            "INSERT INTO presentation_checks("
            "created_at,label,presentation_label,assessment_json) VALUES(?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(),
                _label(label, presentation_label),
                (presentation_label or "")[:200],
                json.dumps(assessment, ensure_ascii=False),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_checks() -> list[dict]:
    conn = db.get_conn()
    with db.LOCK:
        rows = conn.execute(
            "SELECT id,created_at,label,presentation_label FROM presentation_checks ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_check(cid: int) -> dict | None:
    conn = db.get_conn()
    with db.LOCK:
        row = conn.execute("SELECT * FROM presentation_checks WHERE id=?", (cid,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["assessment"] = json.loads(data.pop("assessment_json") or "{}")
    return data


def delete_check(cid: int) -> None:
    conn = db.get_conn()
    with db.LOCK:
        conn.execute("DELETE FROM presentation_checks WHERE id=?", (cid,))
        conn.commit()


def rename_check(cid: int, new_label: str) -> None:
    conn = db.get_conn()
    with db.LOCK:
        conn.execute("UPDATE presentation_checks SET label=? WHERE id=?", (new_label.strip()[:200], cid))
        conn.commit()


def delete_all_checks() -> None:
    conn = db.get_conn()
    with db.LOCK:
        conn.execute("DELETE FROM presentation_checks")
        conn.commit()
