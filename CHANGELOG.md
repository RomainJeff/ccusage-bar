# Changelog

## [Unreleased] - 2026-02-08

### Added - Git-Based Update System
- **In-app update checking and installation**: Users can now update ccusage-bar directly from the menu
  - Menu: "Check for Updates" button (above Quit)
  - Click to check: Contacts GitHub API to check for latest commit
  - If update available: Shows "→ Install Update: <commit message>" with one-click installation
  - Update process: Downloads to `/tmp/`, builds automatically, installs to `/Applications/`, quits app
  - User preferences automatically preserved (stored in `~/.ccusage-bar-prefs.json`)
  - No source directory required - works from bundled app in `/Applications/`

- **Implementation details**:
  - New module: `update_manager.py` (~170 lines)
    - `check_for_updates()`: Uses GitHub API to check latest commit (no local git needed)
    - `install_update()`: Clones repo to temp dir, builds, installs, cleans up
    - Uses `tempfile.mkdtemp()` for isolated builds
    - Automatic cleanup with `shutil.rmtree()` in finally block
    - Progress callbacks: "downloading…" → "building…" → "installing…" → "update ready ✓"
  - Updated `app.py`:
    - Import `UpdateManager` (line ~21)
    - Added `self.check_updates_btn` menu item (line ~151-154)
    - Added update tracking state variables (lines ~88-90)
    - Added update menu items to `_rebuild_menu()` (lines ~207-214)
    - New method `_check_for_updates()` (lines ~767-794): Background GitHub API check
    - New method `_install_update()` (lines ~796-820): Background clone, build, install
  - Updated `setup.py`: Added `update_manager` to includes list (line 17)
  - Manual update script: `update.sh` (~35 lines)
    - Git-based: checks local repo, pulls, rebuilds, reinstalls
    - Requires source directory (unlike in-app method)
    - Fallback for advanced users or if in-app update fails

- **Update flow**:
  1. User clicks "Check for Updates"
  2. App fetches latest commit from GitHub API
  3. Shows "→ Install Update: <commit message>"
  4. User clicks to install
  5. Clones repo to `/tmp/ccusage-bar-update-XXXX/`
  6. Runs `build.sh` in temp directory
  7. Copies built app to `/Applications/`
  8. Deletes temp directory
  9. Quits app (user relaunches manually)

- **Technical advantages**:
  - Zero configuration required (no path dialogs)
  - Source directory can be deleted after initial install
  - Fresh clone every update (no local modifications interfering)
  - Automatic cleanup (temp dir always removed, even on errors)
  - Works from bundled app with no development environment

### Added - Login Item Management
- **Start at Login feature**: Users can now register ccusage-bar to start automatically at login
  - Menu: "Start at Login" menu item in preferences section (above Quit)
  - Click to toggle: "Start at Login" → "Starts on login" (with checkmark)
  - Approval flow: Shows "(approval needed)" if user must approve in System Settings
  - macOS 13+ (Ventura) required (uses modern SMAppService API)

- **Implementation details**:
  - New module: `login_item_manager.py` (143 lines)
    - Uses `SMAppService.mainAppService()` PyObjC binding (not `.mainApp`)
    - Methods: `is_registered()`, `register()`, `unregister()`, `toggle()`
    - Status constants: 0=Not Registered, 1=Enabled, 2=Requires Approval, 3=Not Found
  - Updated `app.py`:
    - Added `self.login_item_toggle` menu item (line ~96-100)
    - Added to menu rebuild in `_rebuild_menu()` (line ~189)
    - New method `_update_login_item_menu()` (line ~203-217): Updates menu text/state
    - New method `_toggle_login_item()` (line ~219-238): Handles toggle with error display
  - Updated `requirements.txt`: Added `pyobjc-framework-ServiceManagement>=10.0`
  - Updated `setup.py`: Added `login_item_manager` to includes list (line 17)
  - Error handling: Shows temporary "⚠️ login item error" in title bar for 3 seconds
  - Works best when app is in `/Applications/` directory

### Changed - Development Guidelines
- **Updated CLAUDE.md**: Added mandatory atomic commit policy for task completion
  - New section: "After Completing Tasks" with commit guidelines
  - Requires commits after every completed task (features, fixes, refactoring)
  - Emphasizes keeping commits atomic (one logical change per commit)
  - Added examples of good vs bad commit practices
  - Updated "Before Committing" checklist to include staging only relevant files

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
  - If refresh triggered >60s ago but display hasn't updated, appends "⚠️" to current price (e.g., "$2.45 ⚠️")
  - Shows stale price with warning indicator instead of replacing it
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
  - Lines 158-169: Stuck state detection in `_tick()` - appends " ⚠️" to current title instead of replacing it
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
