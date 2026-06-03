"""SQLite persistence for snippets and insights."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from . import paths

SCHEMA = """
CREATE TABLE IF NOT EXISTS snippets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    project TEXT NOT NULL DEFAULT '',
    client TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snippets_project ON snippets(project);
CREATE INDEX IF NOT EXISTS idx_snippets_client ON snippets(client);
CREATE INDEX IF NOT EXISTS idx_snippets_tags ON snippets(tags);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    """Create the database file and tables if they do not exist."""
    paths.ensure_data_dir()
    with sqlite3.connect(paths.DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Context manager that yields a connection with row_factory=sqlite3.Row."""
    if not paths.DB_PATH.exists():
        init_db()
    conn = sqlite3.connect(paths.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def insert_snippet(
    title: str,
    content: str,
    tags: str = "",
    project: str = "",
    client: str = "",
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO snippets (title, content, tags, project, client, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (title, content, tags, project, client, _now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_all_snippets(project: str = "", client: str = "") -> list[dict]:
    sql = "SELECT id, title, content, tags, project, client, created_at FROM snippets"
    clauses: list[str] = []
    params: list[str] = []
    if project:
        clauses.append("project = ?")
        params.append(project)
    if client:
        clauses.append("client = ?")
        params.append(client)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY created_at DESC, id DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def search_snippets(query: str) -> list[dict]:
    """Case-insensitive substring search over title, content, and tags."""
    like = f"%{query}%"
    sql = (
        "SELECT id, title, content, tags, project, client, created_at "
        "FROM snippets "
        "WHERE title LIKE ? OR content LIKE ? OR tags LIKE ? "
        "ORDER BY created_at DESC, id DESC"
    )
    with get_conn() as conn:
        rows = conn.execute(sql, (like, like, like)).fetchall()
    return [dict(r) for r in rows]


def insert_insight(text: str, source: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO insights (text, source, created_at) VALUES (?, ?, ?)",
            (text, source, _now_iso()),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_all_insights() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, text, source, created_at FROM insights "
            "ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [dict(r) for r in rows]
