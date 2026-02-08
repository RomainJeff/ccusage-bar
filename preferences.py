import json
import os
from pathlib import Path

PREFS_FILE = os.path.expanduser("~/.ccusage-bar-prefs.json")


def load_preferences():
    """Load preferences from file, or return defaults if file doesn't exist"""
    if not os.path.exists(PREFS_FILE):
        return {}

    try:
        with open(PREFS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_preferences(prefs):
    """Save preferences to file"""
    try:
        with open(PREFS_FILE, 'w') as f:
            json.dump(prefs, f, indent=2)
    except IOError:
        pass  # Silently fail if we can't save


def get_refresh_interval(default=300):
    """Get saved refresh interval in seconds"""
    prefs = load_preferences()
    return prefs.get("refresh_interval", default)


def set_refresh_interval(interval):
    """Save refresh interval"""
    prefs = load_preferences()
    prefs["refresh_interval"] = interval
    save_preferences(prefs)


def get_show_sections(defaults):
    """Get which sections to show. defaults is a dict like {'session': True, 'daily': True, ...}"""
    prefs = load_preferences()
    sections = prefs.get("show_sections", {})

    # Merge with defaults for any missing keys
    result = defaults.copy()
    result.update(sections)
    return result


def set_show_sections(sections):
    """Save which sections to show. sections is a dict like {'session': True, 'daily': True, ...}"""
    prefs = load_preferences()
    prefs["show_sections"] = sections
    save_preferences(prefs)


def get_week_start_day(default="monday"):
    """Get the week start day (monday or sunday)"""
    prefs = load_preferences()
    return prefs.get("week_start_day", default)


def set_week_start_day(day):
    """Save the week start day (monday or sunday)"""
    prefs = load_preferences()
    prefs["week_start_day"] = day
    save_preferences(prefs)
