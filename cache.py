"""SQLite cache for ccusage historical data.

Stores daily cost/token rows so we don't re-fetch immutable historical data
from ccusage on every refresh cycle. Only today's data needs live fetching.

DB location: ~/.ccusage-bar-cache.db
"""

import sqlite3
import json
import os
from datetime import datetime, date

DB_PATH = os.path.expanduser("~/.ccusage-bar-cache.db")
SCHEMA_VERSION = 1


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _maybe_migrate(conn):
    """Drop and recreate if schema version changed."""
    try:
        row = conn.execute(
            "SELECT value FROM cache_meta WHERE key='schema_version'"
        ).fetchone()
        stored = int(row["value"]) if row else 0
    except Exception:
        stored = 0

    if stored < SCHEMA_VERSION:
        conn.execute("DROP TABLE IF EXISTS daily_rows")
        conn.execute("DROP TABLE IF EXISTS cache_meta")


def init_db():
    """Create tables if needed. Returns True on success, False on error."""
    try:
        with _connect() as conn:
            # Check for migration before creating tables
            try:
                conn.execute("SELECT 1 FROM cache_meta LIMIT 1")
                _maybe_migrate(conn)
            except sqlite3.OperationalError:
                pass  # Tables don't exist yet, will be created below

            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_rows (
                    date        TEXT PRIMARY KEY,
                    total_cost  REAL NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    raw_json    TEXT NOT NULL,
                    fetched_at  TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_meta (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT OR IGNORE INTO cache_meta (key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )
            conn.commit()
        return True
    except Exception:
        return False


def get_meta(key, default=None):
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT value FROM cache_meta WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default
    except Exception:
        return default


def set_meta(key, value):
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
                (key, str(value)),
            )
            conn.commit()
    except Exception:
        pass


def upsert_daily_rows(entries):
    """Insert or replace daily rows from ccusage JSON entries."""
    try:
        now = datetime.now().isoformat()
        with _connect() as conn:
            for entry in entries:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_rows
                        (date, total_cost, total_tokens, raw_json, fetched_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    entry["date"],
                    entry.get("totalCost", 0.0),
                    entry.get("totalTokens", 0),
                    json.dumps(entry),
                    now,
                ))
            conn.commit()
    except Exception:
        pass


def get_daily_rows(since_date_str):
    """Return cached daily entry dicts for dates >= since_date_str (YYYY-MM-DD)."""
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT raw_json FROM daily_rows WHERE date >= ? ORDER BY date ASC",
                (since_date_str,),
            ).fetchall()
            return [json.loads(r["raw_json"]) for r in rows]
    except Exception:
        return []
