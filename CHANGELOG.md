# Changelog

## [Unreleased] - 2026-02-08

### Added - Week Start Day Preference
- **Week starts on setting**: Users can now choose whether weeks start on Monday or Sunday
  - Menu: "Week starts on" submenu with Monday/Sunday options (checkmarks show current selection)
  - Default: Monday
  - Preference saved to `~/.ccusage-bar-prefs.json` under `week_start_day` key
  - Affects weekly data display (determines "This week", "Last week" labels and week boundaries)
  - Triggers immediate data refresh when changed to fetch new week groupings

- **Implementation details**:
  - Added `get_week_start_day()` and `set_week_start_day()` to `preferences.py` (lines 60-70)
  - Modified `get_weekly()` in `ccusage_client.py` to accept `week_start_day` parameter (line 61)
  - Passes `--start-of-week` flag to ccusage CLI command
  - Updated `_format_weekly()` in `app.py` to calculate week boundaries based on preference (lines 668-677)
  - Both ccusage CLI and local week calculations use the same week start day for consistency

### Added - Anti-Stale Safeguards
- **Debug logging system** (`~/.ccusage-bar-debug.log`): Tracks all data fetch and display operations
  - Logs initialization, background fetches, data application
  - Auto-rotates to keep only last 100 lines
  - Helps diagnose issues without cluttering console

- **Stuck state detection**: Timer monitors if app is stuck in loading state
  - If refresh triggered >60s ago but display hasn't updated, shows "⚠️ stuck" indicator
  - Helps identify when background thread hangs or data processing fails
  - Previously app could stay stuck on "$0.00" or "loading…" forever

- **Error recovery in `_apply_data()`**:
  - Wraps data application in try/except
  - Shows "⚠️ error" with truncated error message instead of silent failure
  - Provides "Try refreshing" button in error menu
  - Previously any exception would leave app in broken state

- **Error recovery in `_fetch_in_background()`**:
  - Wraps all data fetches in try/except
  - Sets error data with `"error"` key if catastrophic failure
  - Prevents app from hanging if fetch thread crashes
  - Previously thread crashes were silent and left app stuck

### Fixed
- **Stale state issue**: App could get stuck showing $0.00 or outdated data
  - Root cause: Uncaught exceptions in data application or fetch
  - Solution: Multiple layers of error handling + stuck detection + debug logging

### Technical Details

**Debug Log Location**: `~/.ccusage-bar-debug.log`

**Log Events**:
- App initialization
- ccusage availability check
- Background fetch start
- Each data source fetch completion (daily, weekly, monthly, session)
- Pending data detection
- Data application with cost/tokens
- Any errors during fetch or apply

**Example Log Output**:
```
[2026-02-08 10:26:24] App initialized, checking ccusage availability
[2026-02-08 10:26:24] Starting background fetch
[2026-02-08 10:26:28] Daily fetch complete: True
[2026-02-08 10:26:30] Weekly fetch complete: True
[2026-02-08 10:26:33] Monthly fetch complete: True
[2026-02-08 10:26:35] Session fetch complete: True
[2026-02-08 10:26:35] All fetches complete, pending data set
[2026-02-08 10:26:39] Pending data detected, applying...
[2026-02-08 10:26:39] Applied data: today_cost=$4.03, today_tokens=7739122
```

**Stuck Detection Logic**:
- Every 10 seconds (in `_tick()`)
- Checks if `time_since_refresh > 60s` AND `time_since_display > 60s`
- If true: sets title to "⚠️ stuck"
- User can then manually refresh

**Error Display**:
- Title: "⚠️ error"
- Menu shows: "Failed to display data: [first 50 chars of error]"
- Includes refresh button to retry

### Files Changed
- `app.py`: Added debug logging, error handling, stuck detection, week start preference
  - Lines 1-7: Added `sys` import for error handling
  - Lines 16-17: Import week start preference functions (`get_week_start_day`, `set_week_start_day`)
  - Lines 20-44: Debug logging function
  - Line 98: Week start day preference initialization (`self._week_start_day`)
  - Lines 123-130: Week start day menu creation with Monday/Sunday toggle items
  - Line 189: Added week start menu to `_rebuild_menu()`
  - Lines 257-272: Week start day toggle callbacks (`_set_week_start_monday`, `_set_week_start_sunday`)
  - Line 423: Pass `self._week_start_day` to `get_weekly()` in background fetch
  - Lines 668-677: Week calculation in `_format_weekly()` based on preference
  - Lines 116, 346-364, 382-408: Debug log calls
  - Lines 158-168: Stuck state detection in `_tick()`
  - Lines 382-408: Error recovery in `_apply_data()`
  - Lines 365-374: Error recovery in `_fetch_in_background()`

- `ccusage_client.py`: Added week start parameter to weekly fetch
  - Line 61-62: `get_weekly()` now accepts `week_start_day="monday"` parameter (default: "monday")
  - Passes `--start-of-week` flag to ccusage CLI command

- `preferences.py`: Added week start day persistence
  - Lines 60-63: New function `get_week_start_day(default="monday")`
  - Lines 66-70: New function `set_week_start_day(day)`
  - Saved to `~/.ccusage-bar-prefs.json` under `week_start_day` key

### Migration Notes
- No configuration changes required
- Debug log is created automatically on first run
- No performance impact (logging is lightweight)
- If debug log becomes too large, it auto-trims to 100 lines

### Future Improvements
- Add log viewer in menu (optional)
- Configurable log level (verbose/normal/quiet)
- Export logs for bug reports
- Automatic error reporting to developer
