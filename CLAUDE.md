# ccusage-bar - Project Documentation for Claude

> macOS menu bar app for tracking Claude Code usage costs

## Project Overview

**Purpose**: Display Claude Code usage statistics (costs, tokens) in the macOS menu bar with a clean, visually hierarchical interface.

**Tech Stack**: Python 3.12, rumps (menu bar framework), PyObjC (NSAttributedString), py2app (bundling), ccusage CLI

**Current Status**: ✅ Production-ready v1.0.0

## Quick Reference

### System Paths
```bash
# Python
/Users/romainjeff/micromamba/bin/python3  # v3.12.8

# Node/npx (for ccusage)
/Users/romainjeff/.nvm/versions/node/v25.0.0/bin/npx

# App locations
./app.py                        # Run directly
./build.sh                      # Build script
./dist/ccusage-bar.app         # Bundled app
```

### Common Commands
```bash
# Development
python3 app.py                  # Run without building

# Build
./build.sh                      # Clean, build, sign, fix libffi

# Install
cp -r dist/ccusage-bar.app /Applications/

# Test ccusage
npx ccusage daily --json        # Verify ccusage works
```

## Architecture

### Core Components

1. **app.py** (420 lines) - Main application
   - `CcusageBar(rumps.App)` - Main menu bar class
   - Background data fetching via threading
   - NSAttributedString formatting integration
   - Auto-install ccusage if missing
   - Preferences persistence

2. **menu_formatter.py** (158 lines) - Rich text formatting
   - `MenuFormatter` class with font caching
   - NSAttributedString via PyObjC
   - Font sizes: 13pt (headers), 11pt (normal), 10pt (tokens)
   - Color threshold for high costs (≥$5 = red)

3. **ccusage_client.py** - CLI wrapper
   - `run_ccusage(subcommand)` - Subprocess wrapper
   - `get_daily()`, `get_weekly()`, `get_monthly()`, `get_session()`
   - Syncs 1code sessions to ~/.claude/projects
   - Returns None on error (graceful degradation)

4. **preferences.py** - Settings persistence
   - Saves to `~/.ccusage-bar-prefs.json`
   - Refresh interval, section visibility

5. **config.py** - System configuration
   - NPX_PATH, REFRESH_INTERVAL constants

6. **user_config.py** - User-editable settings
   - Section visibility defaults
   - Entry limits per section
   - Data fetch ranges

### Data Flow

```
1. Timer triggers (every 10s) → _tick()
2. If interval elapsed → _fetch_in_background()
3. Background thread:
   - get_daily/weekly/monthly/session()
   - Each calls run_ccusage() subprocess
   - Returns JSON or None
4. Sets self._pending_data
5. _check_pending() (every 2s) → _apply_data()
6. _apply_data():
   - Formats data with MenuFormatter
   - Builds menu items (MenuItem objects)
   - Calls _rebuild_menu()
7. Menu displays with formatting
```

### ccusage JSON Schema

**CRITICAL**: All 4 commands use `totalCost` and `totals.totalCost`, despite docs claiming otherwise.

```json
{
  "daily": [
    { "date": "2026-02-07", "totalCost": 0.15, "totalTokens": 1234, ... }
  ],
  "totals": { "totalCost": 12.34, "totalTokens": 156789 }
}
```

**Note**: `weekly` uses `"week": "2026-02-01"` (Sunday date, not ISO week format)

## Key Features

### 1. Visual Hierarchy (NSAttributedString)
- **Headers**: 13pt bold (`━━━ Cost ━━━`)
- **Labels**: 11pt bold (`Today:`, `Yesterday:`)
- **Values**: 11pt normal (`$0.15`)
- **Tokens**: 10pt normal, gray color (`· 1.2K tokens`)
- **High costs**: Red color for projects ≥$5 (primary info only, tokens stay gray)

**Color scheme**:
- **Primary info** (white/default): Labels, cost values, project names
- **Secondary info** (gray): Token counts and separators (`·`)
- Uses `NSColor.secondaryLabelColor()` which adapts to light/dark mode

**Implementation**: Uses PyObjC to access `menuitem._menuitem.setAttributedTitle_()`

### 2. Auto-Install ccusage
- Detects availability via `npx ccusage --version`
- Shows error menu if not found
- One-click install: `npx npm install -g ccusage`
- Progress feedback: "installing…" → "installed ✓" → auto-refresh

### 3. Relative Dates
- Daily: "Today", "Yesterday", then dates
- Weekly: "This week", "Last week", then dates
- Monthly: "This month", "Last month", then dates

### 4. Smart Refresh
- Auto-refresh with configurable intervals (1m, 2m, 5m, 10m)
- "X minutes ago" relative time display
- Manual refresh button

### 5. Preferences
- Saved to `~/.ccusage-bar-prefs.json`
- Refresh interval persistence
- Section visibility toggles

## Important Technical Details

### PyObjC Imports
```python
# CORRECT - Attributes from AppKit, not Foundation
from Foundation import NSAttributedString, NSMutableAttributedString
from AppKit import NSFont, NSColor, NSFontAttributeName, NSForegroundColorAttributeName
```

### py2app Bundle
```python
# setup.py includes
"includes": ["ccusage_client", "config", "user_config", "preferences", "menu_formatter"]

# Files are in python312.zip
cd dist/ccusage-bar.app/Contents/Resources
python3 -m zipfile -l lib/python312.zip | grep menu_formatter
```

### Threading Pattern
```python
# Background work
def worker():
    # Long-running operation
    result = subprocess.run(...)
    self._pending_data = result

threading.Thread(target=worker, daemon=True).start()

# Periodic check in main thread
@rumps.timer(2)
def _check_pending(self, _):
    if self._pending_data:
        self._apply_data(self._pending_data)
```

### Menu Item Types
```python
# Plain text → auto-formatted if header
"━━━ Cost ━━━"  # Becomes 13pt bold

# MenuItem object → already formatted
item = rumps.MenuItem("text")
MenuFormatter.apply_to_menuitem(item, attr_str)

# None → separator
lines.append(None)
```

## Common Pitfalls & Solutions

### 1. Icon not displaying
**Problem**: Icon path not in bundle or wrong size
**Solution**:
- Use 44x44 for Retina (22pt display)
- Include in setup.py: `data_files=["icon-44.png"]`

### 2. Formatting not working
**Problem**: Import error or wrong attribute names
**Solution**:
```python
# WRONG
from Foundation import NSFontAttributeName  # ❌

# CORRECT
from AppKit import NSFontAttributeName  # ✅
```

### 3. Week dates not matching
**Problem**: ccusage uses Sunday-based weeks, not ISO weeks
**Solution**:
```python
days_since_sunday = (today.weekday() + 1) % 7
this_week_start = today - timedelta(days=days_since_sunday)
```

### 4. App not staying open in background
**Problem**: rumps needs event loop, can't run as background process for testing
**Solution**: Must be launched as GUI app, test via `open dist/ccusage-bar.app`

### 5. Menu rebuilds losing callbacks
**Problem**: Replacing menu items breaks callback references
**Solution**: Keep persistent references or recreate with callbacks:
```python
self.refresh_btn = rumps.MenuItem("Refresh", callback=self._on_refresh)
# Reuse same object in _rebuild_menu()
```

## Git History

```
a93b173 Update README with comprehensive documentation
842dbc9 Add automatic ccusage installation if not found
42dd229 Add NSAttributedString formatting for visual hierarchy in menu items
2904f21 Initial commit: macOS menu bar app for Claude Code usage tracking
```

## Future Enhancements (Ideas)

- [ ] Export data to CSV
- [ ] Cost alerts/notifications when threshold exceeded
- [ ] Graph/sparkline in menu (requires custom NSView)
- [ ] Dark mode icon variant
- [ ] Keyboard shortcuts for refresh
- [ ] Multiple currency support
- [ ] Cost budgets/limits

## Development Guidelines

### Before Making Changes

1. **Read current code** - Don't assume, verify
2. **Test imports** - PyObjC names change between versions
3. **Check git status** - Understand current state
4. **Read MEMORY.md** - Check for known issues

### When Adding Features

1. **Keep rumps simple** - Use PyObjC only when necessary
2. **Background threading** - Long operations must be async
3. **Graceful degradation** - Handle None/errors elegantly
4. **Format consistently** - Use MenuFormatter for all text
5. **Update README FIRST** - Before committing, update README.md to document:
   - New user-facing features in the "Features" section
   - Configuration changes in the "Configuration" section
   - New menu items or UI changes (update screenshots if needed)
   - Troubleshooting notes for common issues

### When Fixing Bugs

1. **Reproduce first** - Understand the issue
2. **Check ccusage output** - Verify JSON schema
3. **Test both modes** - Light and dark menu bar
4. **Rebuild and test** - `./build.sh` before committing

### After Completing Tasks

**CRITICAL**: ALWAYS commit changes after finishing a task, even if the user doesn't explicitly request it.

**Commit Guidelines**:
1. **Keep commits atomic** - One logical change per commit
   - ✅ Good: "Add week start day preference" (single feature)
   - ✅ Good: "Fix token formatting in session view" (single bug fix)
   - ❌ Bad: "Add feature X and fix bug Y" (multiple unrelated changes)

2. **Commit immediately after task completion** - Don't wait for explicit user instruction
   - After adding a feature → commit
   - After fixing a bug → commit
   - After refactoring → commit
   - After updating docs → commit separately if not part of feature/fix

3. **Write clear commit messages**:
   - First line: Brief summary (50 chars or less)
   - Blank line
   - Detailed explanation if needed (wrap at 72 chars)
   - Include Co-Authored-By line

4. **When NOT to commit**:
   - During exploratory work or investigation
   - When user explicitly says not to
   - When changes are incomplete or broken

**Example workflow**:
```bash
# After completing feature
git add <relevant files>
git commit -m "Add configurable week start day preference

Allow users to choose between Monday and Sunday as week start.
Updates preferences.py with new setting and app.py to respect choice.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

### Before Committing

1. **Test locally** - `python3 app.py`
2. **Test bundled** - `./build.sh && open dist/ccusage-bar.app`
3. **Check all sections** - Toggle each view
4. **Verify formatting** - Headers, labels, colors
5. **Update docs** - CRITICAL: Documentation is mandatory, not optional
   - **README.md** - ALWAYS update for user-facing changes:
     * New features → Add to "Features" section with description
     * Config changes → Update "Configuration" section examples
     * UI/menu changes → Update screenshots and descriptions
     * New dependencies → Update "Prerequisites" section
     * Breaking changes → Add to "Troubleshooting" section
   - **CHANGELOG.md** - Add entry for every feature, fix, or significant change
     * Use "Unreleased" section for changes not yet in a tagged release
     * Include technical details: file changes, line numbers, function names
     * Document user-facing changes clearly
   - **CLAUDE.md** - Update if architecture or patterns change
   - **MEMORY.md** - Record learnings and gotchas for future sessions
6. **Stage only relevant files** - Don't include unrelated changes in commit

## README Maintenance Guidelines

**CRITICAL**: The README is the user's primary documentation. Keep it accurate and current.

### When to Update README

**ALWAYS update for**:
- ✅ New features or commands
- ✅ Changed behavior visible to users
- ✅ New configuration options
- ✅ Dependency changes (Python version, new packages)
- ✅ Installation or setup steps changes
- ✅ New menu items or UI elements

**Usually update for**:
- ⚠️ Bug fixes that change behavior (not just internal fixes)
- ⚠️ Performance improvements users will notice
- ⚠️ New troubleshooting solutions

**Don't need to update for**:
- ❌ Internal refactoring (no user-visible changes)
- ❌ Code comments or developer docs
- ❌ CLAUDE.md or MEMORY.md updates

### What to Update in README

1. **Features section** (lines 9-38):
   - Add new features with emoji headers
   - Update existing features if behavior changes
   - Keep formatting consistent (bold, bullets, descriptions)

2. **Screenshots/Examples** (lines 40-71):
   - Update menu text examples if format changes
   - Note: Don't worry about exact costs/dates in examples

3. **Configuration section** (lines 115-151):
   - Add new config options to relevant subsection
   - Update code examples if structure changes
   - Document new default values

4. **Troubleshooting section** (lines 215-241):
   - Add solutions for new common issues
   - Update instructions if fix procedures change

### How to Verify README Accuracy

Before committing, check:
- [ ] All mentioned features actually exist in current code
- [ ] Configuration examples match actual config file structure
- [ ] Installation steps are complete and accurate
- [ ] Code paths and file names are correct
- [ ] No outdated information from previous versions

## File Reference

### Source Files
- `app.py` - Main application (420 lines)
- `menu_formatter.py` - Formatting helper (158 lines)
- `ccusage_client.py` - CLI wrapper (71 lines)
- `preferences.py` - Settings persistence (64 lines)
- `config.py` - System config (7 lines)
- `user_config.py` - User settings (18 lines)
- `setup.py` - py2app config (37 lines)
- `build.sh` - Build script
- `requirements.txt` - Python deps

### Documentation
- `README.md` - User documentation (249 lines)
- `CLAUDE.md` - This file (project reference)
- `MEMORY.md` - Session memory (auto-updated by Claude)
- `CHANGELOG.md` - Version history and detailed change log

### Resources
- `icon-44.png` - Menu bar icon (Retina)
- `.gitignore` - Git exclusions

## Contact & Credits

- Built with [rumps](https://github.com/jaredks/rumps)
- Uses [ccusage](https://github.com/anthropics/ccusage) by Anthropic
- Icon from [Icons8](https://icons8.com)
- License: MIT

---

**Last Updated**: 2026-02-07
**Version**: 1.0.0
**Status**: Production Ready ✅
