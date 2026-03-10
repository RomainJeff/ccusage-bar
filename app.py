import rumps
import threading
import time
import os
import subprocess
import sys
from datetime import datetime, date, timedelta
from ccusage_client import get_daily, get_weekly, get_monthly, get_session
from config import REFRESH_INTERVAL, NPX_PATH
from user_config import (
    SHOW_SESSION, SHOW_DAILY, SHOW_WEEKLY, SHOW_MONTHLY,
    SESSION_LIMIT, DAILY_LIMIT, WEEKLY_LIMIT, MONTHLY_LIMIT
)
from preferences import (
    get_refresh_interval, set_refresh_interval,
    get_show_sections, set_show_sections,
    get_week_start_day, set_week_start_day
)
from menu_formatter import MenuFormatter
from update_manager import UpdateManager

# Simple debug logging to help diagnose issues
DEBUG_LOG = os.path.expanduser("~/.ccusage-bar-debug.log")
def debug_log(msg):
    """Write debug message to log file (only keeps last 100 lines)"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}\n"

        # Read existing logs
        if os.path.exists(DEBUG_LOG):
            with open(DEBUG_LOG, 'r') as f:
                lines = f.readlines()
            lines = lines[-99:]  # Keep last 99 lines
        else:
            lines = []

        # Append new message
        lines.append(log_msg)

        # Write back
        with open(DEBUG_LOG, 'w') as f:
            f.writelines(lines)
    except:
        pass  # Don't let logging errors crash the app

INTERVAL_OPTIONS = [60, 120, 300, 600]
INTERVAL_LABELS = {60: "1 min", 120: "2 min", 300: "5 min", 600: "10 min"}


def fmt(usd):
    return f"${usd:.2f}"


def fmt_tokens(n):
    """Format token count: 1234567 -> 1.2M"""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.0f}K"
    else:
        return str(n)




class CcusageBar(rumps.App):
    def __init__(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon-44.png")
        super().__init__(
            name="ccusage-bar",
            icon=icon_path if os.path.exists(icon_path) else None,
            title="loading…",
            quit_button=None
        )

        # Load preferences
        self._refresh_interval = get_refresh_interval(REFRESH_INTERVAL)
        self._last_refresh_time = 0
        self._last_refresh_display_time = 0
        self._pending_data = None
        self._data_lines = []
        self._last_data = {}  # Initialize to avoid AttributeError
        self._ccusage_available = None
        self._installing_ccusage = False
        self._fetch_active = False

        # Update tracking
        self._update_available = False
        self._update_description = None
        self._installing_update = False

        # Track what to show (load from preferences)
        saved_sections = get_show_sections({
            'session': SHOW_SESSION,
            'daily': SHOW_DAILY,
            'weekly': SHOW_WEEKLY,
            'monthly': SHOW_MONTHLY
        })
        self._show_session = saved_sections['session']
        self._show_daily = saved_sections['daily']
        self._show_weekly = saved_sections['weekly']
        self._show_monthly = saved_sections['monthly']

        # Week start day preference
        self._week_start_day = get_week_start_day("monday")

        # Refresh interval menu
        self.interval_menu = rumps.MenuItem("Refresh interval")
        self._interval_items = {}
        for secs in INTERVAL_OPTIONS:
            label = INTERVAL_LABELS[secs]
            item = rumps.MenuItem(label, callback=self._set_interval)
            item._interval_secs = secs
            item.state = secs == self._refresh_interval
            self._interval_items[secs] = item
            self.interval_menu.add(item)

        # Display config menu
        self.config_menu = rumps.MenuItem("Show sections")
        self.session_toggle = rumps.MenuItem("Projects", callback=self._toggle_session)
        self.session_toggle.state = self._show_session
        self.daily_toggle = rumps.MenuItem("Daily", callback=self._toggle_daily)
        self.daily_toggle.state = self._show_daily
        self.weekly_toggle = rumps.MenuItem("Weekly", callback=self._toggle_weekly)
        self.weekly_toggle.state = self._show_weekly
        self.monthly_toggle = rumps.MenuItem("Monthly", callback=self._toggle_monthly)
        self.monthly_toggle.state = self._show_monthly
        self.config_menu.add(self.session_toggle)
        self.config_menu.add(self.daily_toggle)
        self.config_menu.add(self.weekly_toggle)
        self.config_menu.add(self.monthly_toggle)

        # Week start day menu
        self.week_start_menu = rumps.MenuItem("Week starts on")
        self.monday_toggle = rumps.MenuItem("Monday", callback=self._set_week_start_monday)
        self.monday_toggle.state = self._week_start_day == "monday"
        self.sunday_toggle = rumps.MenuItem("Sunday", callback=self._set_week_start_sunday)
        self.sunday_toggle.state = self._week_start_day == "sunday"
        self.week_start_menu.add(self.monday_toggle)
        self.week_start_menu.add(self.sunday_toggle)

        # Login item toggle
        self.login_item_toggle = rumps.MenuItem(
            "Start at Login",
            callback=self._toggle_login_item
        )
        self._update_login_item_menu()

        # Update menu
        self.check_updates_btn = rumps.MenuItem(
            "Check for Updates",
            callback=self._check_for_updates
        )

        self.status_item = rumps.MenuItem("Last refresh: never")
        self.refresh_btn = rumps.MenuItem("Refresh Now", callback=self._on_refresh)

        self._rebuild_menu([])
        debug_log("App initialized, checking ccusage availability")
        self._check_ccusage_availability()
        self._fetch_in_background()

    def _check_ccusage_availability(self):
        """Check if ccusage is installed and available"""
        def worker():
            try:
                result = subprocess.run(
                    [NPX_PATH, "ccusage", "--version"],
                    capture_output=True,
                    timeout=10,
                    env={**os.environ, "PATH": os.path.dirname(NPX_PATH) + ":" + os.environ.get("PATH", "")}
                )
                self._ccusage_available = result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
                self._ccusage_available = False

        threading.Thread(target=worker, daemon=True).start()

    def _rebuild_menu(self, lines):
        self.menu.clear()
        for line in lines:
            if line is None:
                self.menu.add(rumps.separator)
            elif isinstance(line, rumps.MenuItem):
                # Already a MenuItem (like "View all" submenu or formatted item)
                self.menu.add(line)
            else:
                # Plain string - create MenuItem and apply formatting if it's a header
                item = rumps.MenuItem(line)
                if "━━━" in line:
                    # Format section headers
                    MenuFormatter.apply_to_menuitem(item, MenuFormatter.format_header(line))
                self.menu.add(item)
        if lines:
            self.menu.add(rumps.separator)
        self.menu.add(self.status_item)
        self.menu.add(self.refresh_btn)
        self.menu.add(self.interval_menu)
        self.menu.add(self.config_menu)
        self.menu.add(self.week_start_menu)
        self.menu.add(rumps.separator)
        self.menu.add(self.login_item_toggle)
        self.menu.add(rumps.separator)

        # Update section
        if self._update_available:
            install_item = rumps.MenuItem(
                f"→ Install Update: {self._update_description}",
                callback=self._install_update
            )
            self.menu.add(install_item)
        else:
            self.menu.add(self.check_updates_btn)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))

    @rumps.timer(10)
    def _tick(self, _):
        if time.time() - self._last_refresh_time >= self._refresh_interval:
            self._fetch_in_background()

        # Detect stuck state: if refresh was triggered but no data received in 60s
        # This catches cases where background thread hung or data processing failed
        if self._last_refresh_time > 0:
            time_since_refresh = time.time() - self._last_refresh_time
            time_since_display = time.time() - self._last_refresh_display_time if self._last_refresh_display_time > 0 else 0

            # If refresh was triggered >60s ago but display hasn't updated, we're stuck
            if time_since_refresh > 60 and time_since_display > 60:
                # Append stuck indicator to current price (if it's not already there)
                if not self.title.endswith(" ⚠️") and self.title not in ["⚠️ error", "loading…"]:
                    self.title = self.title + " ⚠️"

        # Update the "Last refresh" time display
        self._update_refresh_status()

    def _set_interval(self, sender):
        self._refresh_interval = sender._interval_secs
        for secs, item in self._interval_items.items():
            item.state = secs == self._refresh_interval
        # Save preference
        set_refresh_interval(self._refresh_interval)

    def _save_section_preferences(self):
        """Save current section visibility preferences"""
        set_show_sections({
            'session': self._show_session,
            'daily': self._show_daily,
            'weekly': self._show_weekly,
            'monthly': self._show_monthly
        })

    def _toggle_session(self, sender):
        self._show_session = not self._show_session
        sender.state = self._show_session
        self._save_section_preferences()
        if self._pending_data is None and hasattr(self, '_last_data'):
            self._apply_data(self._last_data)

    def _toggle_daily(self, sender):
        self._show_daily = not self._show_daily
        sender.state = self._show_daily
        self._save_section_preferences()
        if self._pending_data is None and hasattr(self, '_last_data'):
            self._apply_data(self._last_data)

    def _toggle_weekly(self, sender):
        self._show_weekly = not self._show_weekly
        sender.state = self._show_weekly
        self._save_section_preferences()
        if self._pending_data is None and hasattr(self, '_last_data'):
            self._apply_data(self._last_data)

    def _toggle_monthly(self, sender):
        self._show_monthly = not self._show_monthly
        sender.state = self._show_monthly
        self._save_section_preferences()
        if self._pending_data is None and hasattr(self, '_last_data'):
            self._apply_data(self._last_data)

    def _set_week_start_monday(self, sender):
        self._week_start_day = "monday"
        self.monday_toggle.state = True
        self.sunday_toggle.state = False
        set_week_start_day("monday")
        # Refresh data to get new week groupings
        self._fetch_in_background()

    def _set_week_start_sunday(self, sender):
        self._week_start_day = "sunday"
        self.monday_toggle.state = False
        self.sunday_toggle.state = True
        set_week_start_day("sunday")
        # Refresh data to get new week groupings
        self._fetch_in_background()

    def _update_login_item_menu(self):
        """Update the login item menu text and state based on current status"""
        from login_item_manager import LoginItemManager
        from ServiceManagement import SMAppServiceStatusRequiresApproval

        is_registered, status, error = LoginItemManager.is_registered()

        if status == SMAppServiceStatusRequiresApproval:
            self.login_item_toggle.title = "Start at Login (approval needed)"
            self.login_item_toggle.state = False
        elif is_registered:
            self.login_item_toggle.title = "Starts on login"
            self.login_item_toggle.state = True
        else:
            self.login_item_toggle.title = "Start at Login"
            self.login_item_toggle.state = False

    def _toggle_login_item(self, sender):
        """Toggle the app's login item status"""
        from login_item_manager import LoginItemManager
        import time
        import threading

        new_state, error = LoginItemManager.toggle()

        if error:
            # Show error in title bar briefly
            old_title = self.title
            self.title = "⚠️ login item error"

            # Reset title after a few seconds
            def reset_title():
                time.sleep(3)
                self.title = old_title

            threading.Thread(target=reset_title, daemon=True).start()
        else:
            # Update menu to reflect new state
            self._update_login_item_menu()

    @rumps.timer(2)
    def _check_pending(self, _):
        if self._pending_data is None:
            return
        debug_log("Pending data detected, applying...")
        data = self._pending_data
        self._pending_data = None
        self._apply_data(data)

    def _on_refresh(self, _):
        self.title = "loading…"
        self._fetch_in_background()

    def _install_ccusage(self, _):
        """Install ccusage via npm in background"""
        if self._installing_ccusage:
            return

        self._installing_ccusage = True
        self.title = "installing…"

        def worker():
            try:
                # Install ccusage globally via npm
                result = subprocess.run(
                    [NPX_PATH, "npm", "install", "-g", "ccusage"],
                    capture_output=True,
                    timeout=120,
                    env={**os.environ, "PATH": os.path.dirname(NPX_PATH) + ":" + os.environ.get("PATH", "")}
                )

                if result.returncode == 0:
                    self._ccusage_available = True
                    self.title = "installed ✓"
                    # Wait a bit to show success message
                    time.sleep(2)
                    # Trigger a refresh
                    self._fetch_in_background()
                else:
                    self._ccusage_available = False
                    self.title = "install failed ✗"
                    # Show error for a bit
                    time.sleep(3)
                    self.title = "$0.00"
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                self._ccusage_available = False
                self.title = "install error ✗"
                time.sleep(3)
                self.title = "$0.00"
            finally:
                self._installing_ccusage = False

        threading.Thread(target=worker, daemon=True).start()

    def _show_ccusage_not_found_menu(self):
        """Display menu when ccusage is not installed"""
        self.title = "⚠️ setup required"

        lines = []
        lines.append("━━━ ccusage not found ━━━")

        # Installation status message
        if self._installing_ccusage:
            status_item = rumps.MenuItem("Installing ccusage via npm...")
        else:
            status_item = rumps.MenuItem("ccusage is required but not installed")

        lines.append(status_item)
        lines.append(None)

        # Install button
        if not self._installing_ccusage:
            install_item = rumps.MenuItem("→ Install ccusage now", callback=self._install_ccusage)
            MenuFormatter.apply_to_menuitem(
                install_item,
                MenuFormatter.format_header("→ Install ccusage now")
            )
            lines.append(install_item)
            lines.append(None)

        # Help text
        help_item = rumps.MenuItem("Manual install: npm install -g ccusage")
        lines.append(help_item)

        self._rebuild_menu(lines)

    def _update_refresh_status(self):
        """Update the 'Last refresh' menu item to show time elapsed"""
        if self._last_refresh_display_time == 0:
            self.status_item.title = "Last refresh: never"
            return

        elapsed_seconds = int(time.time() - self._last_refresh_display_time)
        if elapsed_seconds < 60:
            self.status_item.title = "Last refresh: just now"
        else:
            minutes = elapsed_seconds // 60
            if minutes == 1:
                self.status_item.title = "Last refresh: 1 minute ago"
            else:
                self.status_item.title = f"Last refresh: {minutes} minutes ago"

    def _fetch_in_background(self):
        if self._fetch_active:
            debug_log("Fetch already in progress, skipping")
            return
        self._fetch_active = True
        self._last_refresh_time = time.time()
        debug_log("Starting background fetch")

        def worker():
            try:
                daily = get_daily()
                debug_log(f"Daily fetch complete: {daily is not None}")
                weekly = get_weekly(self._week_start_day)
                debug_log(f"Weekly fetch complete: {weekly is not None}")
                monthly = get_monthly()
                debug_log(f"Monthly fetch complete: {monthly is not None}")
                session = get_session()
                debug_log(f"Session fetch complete: {session is not None}")
                self._pending_data = {
                    "daily": daily,
                    "weekly": weekly,
                    "monthly": monthly,
                    "session": session,
                }
                debug_log("All fetches complete, pending data set")
            except Exception as e:
                debug_log(f"Fetch error: {str(e)}")
                # If fetch fails catastrophically, set error data
                self._pending_data = {
                    "daily": None,
                    "weekly": None,
                    "monthly": None,
                    "session": None,
                    "error": str(e)
                }
            finally:
                self._fetch_active = False

        threading.Thread(target=worker, daemon=True).start()

    def _apply_data(self, data):
        # Store last data for toggle callbacks
        self._last_data = data

        try:
            daily = data["daily"]
            weekly = data["weekly"]
            monthly = data["monthly"]
            session = data["session"]

            # Check if ccusage is not available and all data is None
            if self._ccusage_available is False and all(v is None for v in [daily, weekly, monthly, session]):
                self._show_ccusage_not_found_menu()
                return

            today_cost = self._today_cost(daily)
            today_tokens = self._today_tokens(daily)
            self.title = fmt(today_cost)
            debug_log(f"Applied data: today_cost=${today_cost:.2f}, today_tokens={today_tokens}")
        except Exception as e:
            debug_log(f"Error in _apply_data: {str(e)}")
            # If _apply_data fails, show error state instead of staying stuck
            self.title = "⚠️ error"
            lines = [
                "━━━ Error ━━━",
                f"Failed to display data: {str(e)[:50]}",
                None,
                rumps.MenuItem("Try refreshing", callback=self._on_refresh)
            ]
            self._rebuild_menu(lines)
            return

        lines = []

        # Cost summary section with visual hierarchy
        lines.append("━━━ Cost ━━━")

        # Format "Today" with bold label (callback=lambda _: None makes it hoverable but not disabled)
        today_item = rumps.MenuItem(
            f"Today: {fmt(today_cost)} · {fmt_tokens(today_tokens)} tokens",
            callback=lambda _: None
        )
        MenuFormatter.apply_to_menuitem(
            today_item,
            MenuFormatter.format_cost_summary("Today", fmt(today_cost), fmt_tokens(today_tokens))
        )
        lines.append(today_item)

        # Last 30 days summary
        if daily:
            total_cost = daily.get("totals", {}).get("totalCost", 0)
            total_tokens = daily.get("totals", {}).get("totalTokens", 0)
            last30_item = rumps.MenuItem(
                f"Last 30 days: {fmt(total_cost)} · {fmt_tokens(total_tokens)} tokens",
                callback=lambda _: None
            )
            MenuFormatter.apply_to_menuitem(
                last30_item,
                MenuFormatter.format_cost_summary("Last 30 days", fmt(total_cost), fmt_tokens(total_tokens))
            )
            lines.append(last30_item)

        lines.append(None)

        if self._show_session:
            lines.append("━━━ Projects ━━━")
            top_5, all_projects_menu = self._format_projects(session)
            lines.extend(top_5)
            if all_projects_menu:
                lines.append(all_projects_menu)
            lines.append(None)

        if self._show_daily:
            lines.append("━━━ Daily ━━━")
            lines.extend(self._format_daily(daily))
            lines.append(None)

        if self._show_weekly:
            lines.append("━━━ Weekly ━━━")
            lines.extend(self._format_weekly(weekly))
            lines.append(None)

        if self._show_monthly:
            lines.append("━━━ Monthly ━━━")
            lines.extend(self._format_monthly(monthly))

        self._rebuild_menu(lines)

        # Update refresh time
        self._last_refresh_display_time = time.time()
        self._update_refresh_status()

    def _today_cost(self, data):
        if not data:
            return 0
        today_str = date.today().isoformat()
        for entry in data.get("daily", []):
            if entry.get("date") == today_str:
                return entry.get("totalCost", 0)
        return 0

    def _today_tokens(self, data):
        if not data:
            return 0
        today_str = date.today().isoformat()
        for entry in data.get("daily", []):
            if entry.get("date") == today_str:
                return entry.get("totalTokens", 0)
        return 0

    def _format_projects(self, data):
        """Format projects section with top 5 and a 'View all' submenu"""
        if not data:
            return (["(no data)"], None)

        entries = data.get("sessions", [])
        if not entries:
            return (["(no data)"], None)

        # Sort by cost (highest first)
        sorted_entries = sorted(entries, key=lambda x: x.get("totalCost", 0), reverse=True)

        # Format top 5 with formatted MenuItems
        top_5_items = []
        for e in sorted_entries[:5]:
            project_name = e.get("projectPath", e.get("sessionId", "?"))
            if project_name == "Unknown Project":
                project_name = e.get("sessionId", "?")
            # Truncate long project names
            if len(project_name) > 40:
                project_name = project_name[:37] + "..."
            cost = e.get("totalCost", 0)
            tokens = e.get("totalTokens", 0)

            item = rumps.MenuItem(
                f"{project_name}: {fmt(cost)} · {fmt_tokens(tokens)}",
                callback=lambda _: None
            )

            # Apply color threshold for high costs, otherwise normal formatting
            if cost >= 5.0:
                attr_str = MenuFormatter.format_with_color_threshold(
                    f"{project_name}: {fmt(cost)} · {fmt_tokens(tokens)}",
                    cost,
                    threshold=5.0
                )
            else:
                attr_str = MenuFormatter.format_project_line(
                    project_name,
                    fmt(cost),
                    fmt_tokens(tokens)
                )
            MenuFormatter.apply_to_menuitem(item, attr_str)
            top_5_items.append(item)

        # Create "View all" submenu if there are more than 5 projects
        if len(sorted_entries) > 5:
            view_all_menu = rumps.MenuItem("→ View all projects")
            for e in sorted_entries:
                project_name = e.get("projectPath", e.get("sessionId", "?"))
                if project_name == "Unknown Project":
                    project_name = e.get("sessionId", "?")
                cost = e.get("totalCost", 0)
                tokens = e.get("totalTokens", 0)

                # Hoverable but non-actionable
                item = rumps.MenuItem(
                    f"{project_name}: {fmt(cost)} · {fmt_tokens(tokens)}",
                    callback=lambda _: None
                )
                # Format submenu items too
                attr_str = MenuFormatter.format_project_line(
                    project_name,
                    fmt(cost),
                    fmt_tokens(tokens)
                )
                MenuFormatter.apply_to_menuitem(item, attr_str)
                view_all_menu.add(item)
            return (top_5_items, view_all_menu)

        return (top_5_items, None)

    def _format_daily(self, data):
        if not data:
            return ["(no data)"]
        entries = data.get("daily", [])
        items = []
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Reverse to show most recent first
        for e in reversed(entries[-DAILY_LIMIT:]):
            d = e.get("date", "?")
            cost = e.get("totalCost", 0)
            tokens = e.get("totalTokens", 0)

            # Format date label
            if d == today.isoformat():
                label = "Today"
            elif d == yesterday.isoformat():
                label = "Yesterday"
            else:
                label = d

            item = rumps.MenuItem(
                f"{label}: {fmt(cost)} · {fmt_tokens(tokens)}",
                callback=lambda _: None
            )
            attr_str = MenuFormatter.format_cost_summary(label, fmt(cost), fmt_tokens(tokens))
            MenuFormatter.apply_to_menuitem(item, attr_str)
            items.append(item)
        return items

    def _format_weekly(self, data):
        if not data:
            return ["(no data)"]
        entries = data.get("weekly", [])
        items = []

        # Calculate current and last week start dates
        today = date.today()
        if self._week_start_day == "monday":
            # Find the most recent Monday (weekday() returns 0 for Monday)
            days_since_week_start = today.weekday()
        else:
            # Find the most recent Sunday
            days_since_week_start = (today.weekday() + 1) % 7
        this_week_start = today - timedelta(days=days_since_week_start)
        last_week_start = this_week_start - timedelta(days=7)

        this_week_str = this_week_start.isoformat()
        last_week_str = last_week_start.isoformat()

        # Reverse to show most recent first
        for e in reversed(entries[-WEEKLY_LIMIT:]):
            w = e.get("week", "?")
            cost = e.get("totalCost", 0)
            tokens = e.get("totalTokens", 0)

            # Format week label (week format is like "2026-02-01")
            if w == this_week_str:
                label = "This week"
            elif w == last_week_str:
                label = "Last week"
            else:
                label = w

            item = rumps.MenuItem(
                f"{label}: {fmt(cost)} · {fmt_tokens(tokens)}",
                callback=lambda _: None
            )
            attr_str = MenuFormatter.format_cost_summary(label, fmt(cost), fmt_tokens(tokens))
            MenuFormatter.apply_to_menuitem(item, attr_str)
            items.append(item)
        return items

    def _format_monthly(self, data):
        if not data:
            return ["(no data)"]
        entries = data.get("monthly", [])
        items = []

        # Calculate current and last month
        today = date.today()
        current_month = f"{today.year}-{today.month:02d}"
        last_month_date = today.replace(day=1) - timedelta(days=1)
        last_month = f"{last_month_date.year}-{last_month_date.month:02d}"

        # Reverse to show most recent first
        for e in reversed(entries[-MONTHLY_LIMIT:]):
            m = e.get("month", "?")
            cost = e.get("totalCost", 0)
            tokens = e.get("totalTokens", 0)

            # Format month label
            if m == current_month:
                label = "This month"
            elif m == last_month:
                label = "Last month"
            else:
                label = m

            item = rumps.MenuItem(
                f"{label}: {fmt(cost)} · {fmt_tokens(tokens)}",
                callback=lambda _: None
            )
            attr_str = MenuFormatter.format_cost_summary(label, fmt(cost), fmt_tokens(tokens))
            MenuFormatter.apply_to_menuitem(item, attr_str)
            items.append(item)
        return items

    def _check_for_updates(self, _):
        """Check for updates in background using GitHub API"""
        if self._installing_update:
            return

        self.title = "checking…"

        def worker():
            has_update, description, error = UpdateManager.check_for_updates()

            if error:
                debug_log(f"Update check failed: {error}")
                self.title = "⚠️ check failed"
                time.sleep(2)
                self.title = fmt(self._today_cost(self._last_data.get("daily")))
                return

            if not has_update:
                self.title = "✓ up to date"
                time.sleep(2)
                self.title = fmt(self._today_cost(self._last_data.get("daily")))
                return

            # Update available
            self._update_available = True
            self._update_description = description
            debug_log(f"Update available: {description}")

            # Trigger menu rebuild
            self._rebuild_menu(self._data_lines)
            self.title = fmt(self._today_cost(self._last_data.get("daily")))

        threading.Thread(target=worker, daemon=True).start()

    def _install_update(self, _):
        """Install update in background by cloning to temp directory"""
        if self._installing_update:
            return

        self._installing_update = True
        debug_log("Installing update...")

        def progress(msg):
            self.title = msg

        def worker():
            success, error = UpdateManager.install_update(progress_callback=progress)

            if success:
                debug_log("Update installed successfully")
                self.title = "update ready ✓"
                time.sleep(2)

                # App will quit, user relaunches from /Applications/
                # Preferences preserved automatically (~/.ccusage-bar-prefs.json)
                rumps.quit_application()
            else:
                debug_log(f"Update failed: {error}")
                self.title = "update failed"
                time.sleep(3)
                self.title = fmt(self._today_cost(self._last_data.get("daily")))
                self._installing_update = False
                self._update_available = False

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    CcusageBar().run()
