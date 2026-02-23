import subprocess
import json
import os
import glob
import time
from datetime import datetime, timedelta
from config import NPX_PATH, CCUSAGE_PKG
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


def _cleanup_stale_symlinks():
    """Remove broken 1code-* symlinks to prepare for fresh sync."""
    if not os.path.isdir(CLAUDE_PROJECTS):
        return 0

    removed = 0
    for entry in os.listdir(CLAUDE_PROJECTS):
        if not entry.startswith("1code-"):
            continue

        link = os.path.join(CLAUDE_PROJECTS, entry)
        # Check if symlink exists but target doesn't (broken)
        if os.path.islink(link) and not os.path.exists(link):
            try:
                os.unlink(link)
                _debug_log(f"Removed broken symlink: {entry}")
                removed += 1
            except OSError as e:
                _debug_log(f"Failed to remove {entry}: {e}")

    return removed


def _sync_1code_symlinks():
    """Symlink 1code session JSONL files into ~/.claude/projects so ccusage can find them."""
    # Check if resync needed (performance optimization)
    if not _should_resync():
        return  # Skip sync if workspaces unchanged

    if not os.path.isdir(ONECODE_SESSIONS):
        _debug_log("1code sessions directory not found")
        return

    # Ensure target directory exists
    try:
        os.makedirs(CLAUDE_PROJECTS, exist_ok=True)
    except OSError as e:
        _debug_log(f"Failed to create projects directory: {e}")
        return

    # Step 1: Clean up broken symlinks first
    removed = _cleanup_stale_symlinks()
    if removed > 0:
        _debug_log(f"Cleanup: removed {removed} broken symlinks")

    # Step 2: Scan for 1code workspaces
    pattern = os.path.join(ONECODE_SESSIONS, "*/projects/*")
    session_dirs = glob.glob(pattern)

    if not session_dirs:
        _debug_log("No 1code workspaces found")
        return

    created = 0
    skipped = 0
    errors = 0

    # Step 3: Create symlinks for each workspace project
    for session_dir in session_dirs:
        project_name = os.path.basename(session_dir)
        name = "1code-" + project_name
        link = os.path.join(CLAUDE_PROJECTS, name)

        # Check if symlink already exists (use lexists to detect broken links too)
        if os.path.lexists(link):
            # Verify it points to correct target
            if os.path.islink(link):
                try:
                    existing_target = os.readlink(link)
                    if existing_target == session_dir:
                        skipped += 1
                        continue  # Already correct

                    # Collision: different workspace, same project name
                    # Extract session ID from path: .../claude-sessions/<session_id>/projects/<project>
                    try:
                        session_id = os.path.basename(os.path.dirname(os.path.dirname(session_dir)))
                        name = f"1code-{project_name}-{session_id[:8]}"
                        link = os.path.join(CLAUDE_PROJECTS, name)
                        _debug_log(f"Name collision for '{project_name}', using: {name}")
                    except (IndexError, AttributeError):
                        # Fallback: use hash of full path if structure unexpected
                        import hashlib
                        session_id = hashlib.md5(session_dir.encode()).hexdigest()[:8]
                        name = f"1code-{project_name}-{session_id}"
                        link = os.path.join(CLAUDE_PROJECTS, name)
                        _debug_log(f"Name collision for '{project_name}' (fallback hash), using: {name}")
                except OSError as e:
                    _debug_log(f"Failed to read existing symlink {name}: {e}")
                    errors += 1
                    continue

        # Create symlink
        try:
            os.symlink(session_dir, link)
            _debug_log(f"Created symlink: {name} -> {session_dir}")
            created += 1
        except FileExistsError:
            _debug_log(f"Symlink already exists (race condition?): {name}")
            skipped += 1
        except PermissionError as e:
            _debug_log(f"Permission denied creating {name}: {e}")
            errors += 1
        except OSError as e:
            _debug_log(f"Failed to create symlink {name}: {e} (errno: {e.errno})")
            errors += 1

    # Summary log
    _debug_log(f"Sync complete: created {created}, skipped {skipped}, errors {errors}")


def run_ccusage(subcommand, extra_args=None):
    cmd = [NPX_PATH, CCUSAGE_PKG, subcommand, "--json"]
    if extra_args:
        cmd.extend(extra_args)

    env = os.environ.copy()
    env["PATH"] = os.path.dirname(NPX_PATH) + ":" + env.get("PATH", "")
    env.pop("CLAUDE_CONFIG_DIR", None)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, env=env,
            cwd=os.path.expanduser("~")
        )
        if result.returncode != 0:
            _debug_log(f"ccusage {subcommand} failed (rc={result.returncode}): {result.stderr[:200]}")
            return None
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        _debug_log(f"ccusage {subcommand} timed out after 30s")
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
