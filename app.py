import rumps
import threading
import time
import os
from datetime import datetime, date, timedelta
from ccusage_client import get_daily, get_weekly, get_monthly, get_session
from config import REFRESH_INTERVAL
from user_config import (
    SHOW_SESSION, SHOW_DAILY, SHOW_WEEKLY, SHOW_MONTHLY,
    SESSION_LIMIT, DAILY_LIMIT, WEEKLY_LIMIT, MONTHLY_LIMIT
)
from preferences import (
    get_refresh_interval, set_refresh_interval,
    get_show_sections, set_show_sections
)

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

        self.status_item = rumps.MenuItem("Last refresh: never")
        self.refresh_btn = rumps.MenuItem("Refresh Now", callback=self._on_refresh)

        self._rebuild_menu([])
        self._fetch_in_background()

    def _rebuild_menu(self, lines):
        self.menu.clear()
        for line in lines:
            if line is None:
                self.menu.add(rumps.separator)
            elif isinstance(line, rumps.MenuItem):
                # Already a MenuItem (like "View all" submenu)
                self.menu.add(line)
            else:
                # No callback = disabled/non-interactive (no hover effect)
                self.menu.add(rumps.MenuItem(line))
        if lines:
            self.menu.add(rumps.separator)
        self.menu.add(self.status_item)
        self.menu.add(self.refresh_btn)
        self.menu.add(self.interval_menu)
        self.menu.add(self.config_menu)
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))

    @rumps.timer(10)
    def _tick(self, _):
        if time.time() - self._last_refresh_time >= self._refresh_interval:
            self._fetch_in_background()
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

    @rumps.timer(2)
    def _check_pending(self, _):
        if self._pending_data is None:
            return
        data = self._pending_data
        self._pending_data = None
        self._apply_data(data)

    def _on_refresh(self, _):
        self.title = "loading…"
        self._fetch_in_background()

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
        self._last_refresh_time = time.time()

        def worker():
            daily = get_daily()
            weekly = get_weekly()
            monthly = get_monthly()
            session = get_session()
            self._pending_data = {
                "daily": daily,
                "weekly": weekly,
                "monthly": monthly,
                "session": session,
            }

        threading.Thread(target=worker, daemon=True).start()

    def _apply_data(self, data):
        # Store last data for toggle callbacks
        self._last_data = data

        daily = data["daily"]
        weekly = data["weekly"]
        monthly = data["monthly"]
        session = data["session"]

        today_cost = self._today_cost(daily)
        today_tokens = self._today_tokens(daily)
        self.title = fmt(today_cost)

        lines = []

        # Cost summary section with visual hierarchy
        lines.append("━━━ Cost ━━━")
        lines.append(f"Today: {fmt(today_cost)} · {fmt_tokens(today_tokens)} tokens")

        # Last 30 days summary
        if daily:
            total_cost = daily.get("totals", {}).get("totalCost", 0)
            total_tokens = daily.get("totals", {}).get("totalTokens", 0)
            lines.append(f"Last 30 days: {fmt(total_cost)} · {fmt_tokens(total_tokens)} tokens")

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

        # Format top 5
        top_5_lines = []
        for e in sorted_entries[:5]:
            project_name = e.get("projectPath", e.get("sessionId", "?"))
            if project_name == "Unknown Project":
                project_name = e.get("sessionId", "?")
            # Truncate long project names
            if len(project_name) > 40:
                project_name = project_name[:37] + "..."
            cost = e.get("totalCost", 0)
            tokens = e.get("totalTokens", 0)
            top_5_lines.append(f"{project_name}: {fmt(cost)} · {fmt_tokens(tokens)}")

        # Create "View all" submenu if there are more than 5 projects
        if len(sorted_entries) > 5:
            view_all_menu = rumps.MenuItem("→ View all projects")
            for e in sorted_entries:
                project_name = e.get("projectPath", e.get("sessionId", "?"))
                if project_name == "Unknown Project":
                    project_name = e.get("sessionId", "?")
                cost = e.get("totalCost", 0)
                tokens = e.get("totalTokens", 0)
                # No callback = disabled/non-interactive
                item = rumps.MenuItem(f"{project_name}: {fmt(cost)} · {fmt_tokens(tokens)}")
                view_all_menu.add(item)
            return (top_5_lines, view_all_menu)

        return (top_5_lines, None)

    def _format_daily(self, data):
        if not data:
            return ["(no data)"]
        entries = data.get("daily", [])
        lines = []
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

            lines.append(f"{label}: {fmt(cost)} · {fmt_tokens(tokens)}")
        return lines

    def _format_weekly(self, data):
        if not data:
            return ["(no data)"]
        entries = data.get("weekly", [])
        lines = []

        # Calculate current and last week start dates (Sundays)
        today = date.today()
        # Find the most recent Sunday
        days_since_sunday = (today.weekday() + 1) % 7
        this_week_start = today - timedelta(days=days_since_sunday)
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

            lines.append(f"{label}: {fmt(cost)} · {fmt_tokens(tokens)}")
        return lines

    def _format_monthly(self, data):
        if not data:
            return ["(no data)"]
        entries = data.get("monthly", [])
        lines = []

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

            lines.append(f"{label}: {fmt(cost)} · {fmt_tokens(tokens)}")
        return lines


if __name__ == "__main__":
    CcusageBar().run()
