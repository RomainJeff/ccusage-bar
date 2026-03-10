import subprocess
import json
import os
import glob
import signal
import time
from datetime import datetime, timedelta
from config import NPX_PATH, CCUSAGE_PKG, SUBPROCESS_TIMEOUT
from user_config import (
    DAILY_SINCE_DAYS, WEEKLY_SINCE_DAYS, MONTHLY_SINCE_DAYS, SESSION_SINCE_DAYS
)

ONECODE_SESSIONS = os.path.expanduser(
    "~/Library/Application Support/21st-desktop/claude-sessions"
)
CLAUDE_PROJECTS = os.path.expanduser("~/.claude/projects")

# Cache for symlink sync to avoid redundant scans
_last_sync_time = 0
_last_workspace_snapshot = {}

# Debug logging
DEBUG_LOG = os.path.expanduser("~/.ccusage-bar-debug.log")


def _debug_log(msg):
    """Local debug logging for ccusage_client (mirrors app.py implementation)"""
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [ccusage] {msg}\n"

        if os.path.exists(DEBUG_LOG):
            with open(DEBUG_LOG, 'r') as f:
                lines = f.readlines()
            lines = lines[-99:]
        else:
            lines = []

        lines.append(log_msg)

        with open(DEBUG_LOG, 'w') as f:
            f.writelines(lines)
    except:
        pass


def _since_date(days=30):
    return (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")


def _should_resync():
    """Check if workspaces changed since last sync (use mtime to detect changes)."""
    global _last_sync_time, _last_workspace_snapshot

    # Minimum 5 minute interval between syncs (even if workspaces changed)
    now = time.time()
    if now - _last_sync_time < 300:  # 5 minutes = 300 seconds
        return False

    # Check if 1code sessions directory exists
    if not os.path.isdir(ONECODE_SESSIONS):
        return False

    # Build snapshot of current workspace directories with mtimes
    current_snapshot = {}
    try:
        for session_dir in glob.glob(os.path.join(ONECODE_SESSIONS, "*")):
            if os.path.isdir(session_dir):
                mtime = os.path.getmtime(session_dir)
                current_snapshot[session_dir] = mtime
    except OSError as e:
        _debug_log(f"Error scanning workspaces for mtime: {e}")
        return False

    # Compare snapshots
    if current_snapshot != _last_workspace_snapshot:
        _debug_log(f"Workspace changes detected: {len(current_snapshot)} workspaces")
        _last_workspace_snapshot = current_snapshot
        _last_sync_time = now
        return True

    # No changes
    return False


def _remove_all_1code_symlinks():
    """Remove ALL 1code-* symlinks to prepare for a fresh rebuild."""
    if not os.path.isdir(CLAUDE_PROJECTS):
        return 0

    removed = 0
    for entry in os.listdir(CLAUDE_PROJECTS):
        if not entry.startswith("1code-"):
            continue

        link = os.path.join(CLAUDE_PROJECTS, entry)
        if os.path.islink(link):
            try:
                os.unlink(link)
                removed += 1
            except OSError as e:
                _debug_log(f"Failed to remove {entry}: {e}")

    return removed


MAX_SESSIONS_PER_PROJECT = 20


def _sync_1code_symlinks():
    """Symlink recent 1code session projects into ~/.claude/projects for ccusage.

    Wipe-and-rebuild strategy: removes all existing 1code-* symlinks, then
    recreates only the most recent MAX_SESSIONS_PER_PROJECT sessions per
    unique project name.
    """
    if not _should_resync():
        return

    if not os.path.isdir(ONECODE_SESSIONS):
        _debug_log("1code sessions directory not found")
        return

    try:
        os.makedirs(CLAUDE_PROJECTS, exist_ok=True)
    except OSError as e:
        _debug_log(f"Failed to create projects directory: {e}")
        return

    # Step 1: Wipe all existing 1code symlinks
    removed = _remove_all_1code_symlinks()

    # Step 2: Scan and group by project name
    pattern = os.path.join(ONECODE_SESSIONS, "*/projects/*")
    session_dirs = glob.glob(pattern)

    if not session_dirs:
        _debug_log("No 1code workspaces found")
        return

    # Group session dirs by project name, with mtime for sorting
    projects = {}
    for session_dir in session_dirs:
        project_name = os.path.basename(session_dir)
        try:
            mtime = os.path.getmtime(session_dir)
        except OSError:
            continue
        projects.setdefault(project_name, []).append((mtime, session_dir))

    # Step 3: Keep only the N most recent sessions per project
    created = 0
    skipped = 0
    errors = 0

    for project_name, sessions in projects.items():
        # Sort by mtime descending, keep only the most recent
        sessions.sort(reverse=True)
        kept = sessions[:MAX_SESSIONS_PER_PROJECT]
        skipped += len(sessions) - len(kept)

        for i, (_, session_dir) in enumerate(kept):
            if i == 0:
                name = "1code-" + project_name
            else:
                session_id = os.path.basename(os.path.dirname(os.path.dirname(session_dir)))
                name = f"1code-{project_name}-{session_id[:8]}"
            link = os.path.join(CLAUDE_PROJECTS, name)

            try:
                os.symlink(session_dir, link)
                created += 1
            except FileExistsError:
                pass
            except OSError as e:
                _debug_log(f"Failed to create symlink {name}: {e}")
                errors += 1

    _debug_log(f"Sync: removed {removed}, created {created}, skipped_old {skipped}, errors {errors} ({len(projects)} projects)")


def run_ccusage(subcommand, extra_args=None):
    cmd = [NPX_PATH, CCUSAGE_PKG, subcommand, "--json"]
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    env["PATH"] = os.path.dirname(NPX_PATH) + ":" + env.get("PATH", "")
    env.pop("CLAUDE_CONFIG_DIR", None)

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=os.path.expanduser("~"),
            start_new_session=True,
        )
        stdout, stderr = proc.communicate(timeout=SUBPROCESS_TIMEOUT)
        if proc.returncode != 0:
            _debug_log(f"ccusage {subcommand} failed (rc={proc.returncode}): {stderr[:200]}")
            return None
        return json.loads(stdout)
    except subprocess.TimeoutExpired:
        _debug_log(f"ccusage {subcommand} timed out after {SUBPROCESS_TIMEOUT}s")
        if proc is not None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            proc.wait()
        return None
    except json.JSONDecodeError as e:
        _debug_log(f"ccusage {subcommand} invalid JSON: {e}")
        return None
    except FileNotFoundError:
        _debug_log(f"ccusage {subcommand} binary not found: {NPX_PATH}")
        return None


def get_daily():
    _sync_1code_symlinks()
    return run_ccusage("daily", ["--since", _since_date(DAILY_SINCE_DAYS)])


def get_weekly(week_start_day="monday"):
    return run_ccusage("weekly", ["--since", _since_date(WEEKLY_SINCE_DAYS), "--start-of-week", week_start_day])


def get_monthly():
    return run_ccusage("monthly", ["--since", _since_date(MONTHLY_SINCE_DAYS)])


def get_session():
    return run_ccusage("session", ["--since", _since_date(SESSION_SINCE_DAYS)])
