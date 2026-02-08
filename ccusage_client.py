import subprocess
import json
import os
import glob
from datetime import datetime, timedelta
from config import NPX_PATH, CCUSAGE_PKG
from user_config import (
    DAILY_SINCE_DAYS, WEEKLY_SINCE_DAYS, MONTHLY_SINCE_DAYS, SESSION_SINCE_DAYS
)

ONECODE_SESSIONS = os.path.expanduser(
    "~/Library/Application Support/21st-desktop/claude-sessions"
)
CLAUDE_PROJECTS = os.path.expanduser("~/.claude/projects")


def _since_date(days=30):
    return (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")


def _sync_1code_symlinks():
    """Symlink 1code session JSONL files into ~/.claude/projects so ccusage can find them."""
    if not os.path.isdir(ONECODE_SESSIONS):
        return
    for session_dir in glob.glob(os.path.join(ONECODE_SESSIONS, "*/projects/*")):
        name = "1code-" + os.path.basename(session_dir)
        link = os.path.join(CLAUDE_PROJECTS, name)
        if not os.path.exists(link):
            try:
                os.symlink(session_dir, link)
            except OSError:
                pass


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
            return None
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
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
