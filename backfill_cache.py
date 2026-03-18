#!/usr/bin/env python3
"""One-shot script to backfill the ccusage cache with 60 days of historical data.

Rebuilds all 1code symlinks (up to 500 sessions per project), wipes the cache,
fetches 60 days from ccusage, and stores them as the immutable baseline.

Usage:
    python3 backfill_cache.py
"""

import subprocess
import json
import os
import sys
import sqlite3
import glob
from datetime import datetime, date, timedelta

# --- Config (copied from project modules to stay self-contained) ---

NPX_PATH = "/Users/romainjeff/.nvm/versions/node/v25.0.0/bin/npx"
CCUSAGE_PKG = "ccusage@18.0.9"
SUBPROCESS_TIMEOUT = 300  # generous timeout for large fetch

ONECODE_SESSIONS = os.path.expanduser(
    "~/Library/Application Support/21st-desktop/claude-sessions"
)
CLAUDE_PROJECTS = os.path.expanduser("~/.claude/projects")
DB_PATH = os.path.expanduser("~/.ccusage-bar-cache.db")

BACKFILL_DAYS = 60
MAX_SESSIONS_PER_PROJECT = 500

SCHEMA_VERSION = 2


# --- Symlink rebuild ---

def remove_all_1code_symlinks():
    if not os.path.isdir(CLAUDE_PROJECTS):
        return 0
    removed = 0
    for entry in os.listdir(CLAUDE_PROJECTS):
        if not entry.startswith("1code-"):
            continue
        link = os.path.join(CLAUDE_PROJECTS, entry)
        if os.path.islink(link):
            os.unlink(link)
            removed += 1
    return removed


def rebuild_symlinks():
    os.makedirs(CLAUDE_PROJECTS, exist_ok=True)
    removed = remove_all_1code_symlinks()
    print(f"  Removed {removed} old 1code-* symlinks")

    pattern = os.path.join(ONECODE_SESSIONS, "*/projects/*")
    session_dirs = glob.glob(pattern)
    if not session_dirs:
        print("  No 1code session dirs found")
        return

    projects = {}
    for session_dir in session_dirs:
        project_name = os.path.basename(session_dir)
        try:
            mtime = os.path.getmtime(session_dir)
        except OSError:
            continue
        projects.setdefault(project_name, []).append((mtime, session_dir))

    created = 0
    for project_name, sessions in projects.items():
        sessions.sort(reverse=True)
        kept = sessions[:MAX_SESSIONS_PER_PROJECT]
        for i, (_, session_dir) in enumerate(kept):
            if i == 0:
                name = "1code-" + project_name
            else:
                session_id = os.path.basename(
                    os.path.dirname(os.path.dirname(session_dir))
                )
                name = f"1code-{project_name}-{session_id[:8]}"
            link = os.path.join(CLAUDE_PROJECTS, name)
            try:
                os.symlink(session_dir, link)
                created += 1
            except FileExistsError:
                pass

    total_sessions = sum(len(s) for s in projects.values())
    print(f"  Created {created} symlinks ({len(projects)} projects, {total_sessions} total sessions)")


# --- Cache reset ---

def reset_cache():
    """Drop and recreate the cache DB with a clean schema."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("DROP TABLE IF EXISTS daily_rows")
    conn.execute("DROP TABLE IF EXISTS cache_meta")
    conn.execute("""
        CREATE TABLE daily_rows (
            date        TEXT PRIMARY KEY,
            total_cost  REAL NOT NULL,
            total_tokens INTEGER NOT NULL,
            raw_json    TEXT NOT NULL,
            fetched_at  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE cache_meta (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute(
        "INSERT INTO cache_meta (key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.execute(
        "INSERT INTO cache_meta (key, value) VALUES (?, ?)",
        ("last_full_fetch_date", date.today().isoformat()),
    )
    conn.commit()
    conn.close()
    print(f"  Cache reset: {DB_PATH}")


# --- Fetch & store ---

def fetch_daily(days):
    since = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    cmd = [NPX_PATH, CCUSAGE_PKG, "daily", "--json", "--since", since]

    env = os.environ.copy()
    env["PATH"] = os.path.dirname(NPX_PATH) + ":" + env.get("PATH", "")
    env.pop("CLAUDE_CONFIG_DIR", None)

    print(f"  Running: {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=os.path.expanduser("~"),
        timeout=SUBPROCESS_TIMEOUT,
    )
    if proc.returncode != 0:
        print(f"  ERROR: ccusage failed (rc={proc.returncode})")
        print(f"  stderr: {proc.stderr[:500]}")
        sys.exit(1)

    return json.loads(proc.stdout)


def store_rows(result):
    entries = result.get("daily", [])
    if not entries:
        print("  No daily entries returned")
        return 0

    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
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
    conn.close()
    return len(entries)


# --- Main ---

def main():
    print(f"=== ccusage-bar cache backfill ({BACKFILL_DAYS} days, {MAX_SESSIONS_PER_PROJECT} sessions/project) ===\n")

    print("[1/4] Rebuilding 1code symlinks...")
    rebuild_symlinks()

    print("\n[2/4] Resetting cache DB...")
    reset_cache()

    print(f"\n[3/4] Fetching {BACKFILL_DAYS} days from ccusage...")
    result = fetch_daily(BACKFILL_DAYS)

    print("\n[4/4] Storing in cache...")
    count = store_rows(result)

    totals = result.get("totals", {})
    total_cost = totals.get("totalCost", 0)
    total_tokens = totals.get("totalTokens", 0)

    print(f"\n=== Done! ===")
    print(f"  {count} days cached")
    print(f"  Total cost: ${total_cost:.2f}")
    print(f"  Total tokens: {total_tokens:,}")
    print(f"  Cache: {DB_PATH}")
    print(f"\nThese values are now locked. The app will only update today going forward.")


if __name__ == "__main__":
    main()
