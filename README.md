# ccusage-bar

![Claude Code icon in menu bar](icon-44.png)

macOS menu bar app showing Claude Code usage costs in USD.

<img width="283" height="772" alt="image" src="https://github.com/user-attachments/assets/76e0f574-c68b-47b3-8a5a-7b32761fcf52" />

## Features

### 📊 **Visual Hierarchy**
- **NSAttributedString formatting** with multiple font sizes (13pt headers, 11pt normal, 10pt secondary info)
- **Bold labels** for section headers and cost summaries
- **Color-coded alerts** for high-cost projects (≥$5.00 in red)
- **Adaptive colors** for light/dark mode (uses `NSColor.secondaryLabelColor()` for token counts)
- **Retina-ready Claude icon** (44x44) in menu bar

### 💰 **Usage Tracking**
- **Today's cost** displayed in menu bar next to icon
- **Four data views**: Cost summary, Projects, Daily, Weekly, Monthly
- **Relative date labels**: "Today", "Yesterday", "This week", "Last week", etc.
- **Token counts** with compact formatting (1.2M, 15K, etc.)
- **Projects sorted by cost** with top 5 shown, rest in "View all projects" submenu

### 🔄 **Smart Refresh**
- **Auto-refresh** with configurable intervals (1min, 2min, 5min, 10min)
- **"X minutes ago"** relative refresh time display
- **Manual refresh** button in menu
- **Stuck state detection** with warning indicator (⚠️) if data fetch hangs

### ⚙️ **Configuration**
- **Persistent preferences** saved to `~/.ccusage-bar-prefs.json`
- **Toggle sections** on/off (Projects, Daily, Weekly, Monthly)
- **Customizable refresh interval** via menu
- **Week start day preference** (Monday or Sunday)
- **Start at Login** toggle for automatic startup
- Reads data from both `~/.claude` and 1code sessions

### 🚀 **Auto-Installation**
- **Automatic ccusage detection** on startup
- **One-click installation** if ccusage not found
- Runs `npm install -g ccusage` in background
- Shows installation progress in menu bar

### 🔍 **Debug Logging**
- **Debug log file** at `~/.ccusage-bar-debug.log`
- Automatically maintains last 100 log entries
- Helps diagnose data fetch and display issues

## Screenshots

### Menu Bar

The app displays today's cost next to the Claude icon in the menu bar:

```
🤖 $0.15
```

### Menu Structure

**Normal view (all sections enabled):**
```
━━━ Cost ━━━                    [13pt bold]
Today: $0.15 · 1.2K tokens      [11pt bold: label, normal: value, 10pt gray: tokens]
Last 30 days: $12.34 · 156K tokens

━━━ Projects ━━━                [13pt bold]
/path/to/project1: $5.67 · 45K  [RED if ≥$5, 11pt bold: name, normal: cost, 10pt gray: tokens]
/path/to/project2: $2.34 · 12K
/path/to/project3: $1.23 · 8K
→ View all projects             [submenu with all projects]

━━━ Daily ━━━                   [13pt bold]
Today: $0.15 · 1.2K tokens
Yesterday: $0.89 · 8K tokens
2026-02-06: $1.23 · 10K tokens
2026-02-05: $0.67 · 5K tokens

━━━ Weekly ━━━                  [13pt bold]
This week: $2.34 · 18K tokens
Last week: $5.67 · 45K tokens
2026-01-26: $3.21 · 25K tokens

━━━ Monthly ━━━                 [13pt bold]
This month: $12.34 · 156K tokens
Last month: $23.45 · 234K tokens

Last refresh: 2 minutes ago
────────────────────────────
Refresh Now
Refresh interval ▸
  ○ 1 min
  ○ 2 min
  ● 5 min
  ○ 10 min
Show sections ▸
  ☑ Projects
  ☑ Daily
  ☑ Weekly
  ☑ Monthly
Week starts on ▸
  ● Monday
  ○ Sunday
────────────────────────────
☑ Starts on login
────────────────────────────
Quit
```

**Setup view (ccusage not installed):**
```
⚠️ setup required

━━━ ccusage not found ━━━
ccusage is required but not installed

→ Install ccusage now           [clickable, 13pt bold]

Manual install: npm install -g ccusage
```

**Installing view:**
```
installing…

━━━ ccusage not found ━━━
Installing ccusage via npm...
```

**Error state:**
```
⚠️ error

━━━ Error ━━━
Failed to display data: [error message]

Try refreshing
```

**Stuck state (data fetch hanging):**
```
$0.15 ⚠️

[Menu shows last known data with warning]
```

## Installation

### Prerequisites

**Required:**
- macOS 11+ (Big Sur or later)
- Python 3.12 or later
- Node.js 14+ and npm (for ccusage CLI)

**Python packages** (installed automatically via requirements.txt):
- `rumps>=0.4.0` - macOS menu bar framework
- `py2app>=0.28` - App bundling tool
- `pyobjc-framework-ServiceManagement>=10.0` - Login item management

### Quick Install

1. **Clone the repository:**
   ```bash
   git clone git@github.com:RomainJeff/ccusage-bar.git
   cd ccusage-bar
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

   Or with a specific Python installation:
   ```bash
   /path/to/python3 -m pip install -r requirements.txt
   ```

3. **Build the app:**
   ```bash
   chmod +x build.sh
   ./build.sh
   ```

   This will:
   - Clean previous builds
   - Create a standalone .app bundle with py2app
   - Fix libffi library dependencies
   - Code sign the app
   - Output to `dist/ccusage-bar.app`

4. **Install to Applications:**
   ```bash
   cp -r dist/ccusage-bar.app /Applications/
   ```

5. **Launch the app:**
   ```bash
   open /Applications/ccusage-bar.app
   ```

   Or double-click from Finder.

6. **Enable Start at Login (optional):**
   - Click the menu bar icon
   - Select "Start at Login"
   - Approve in System Settings if prompted

### ccusage Installation

The app will automatically detect if `ccusage` is not installed and offer to install it:

1. Launch the app
2. If ccusage is missing, you'll see "⚠️ setup required" in the menu bar
3. Click "→ Install ccusage now" from the menu
4. Wait for installation to complete (shows "installing…" then "installed ✓")

**Manual installation** (if needed):
```bash
npm install -g ccusage
```

**Verify installation:**
```bash
npx ccusage --version
```

### Updating

To update to the latest version:

```bash
cd ccusage-bar
git pull origin main
./build.sh
cp -r dist/ccusage-bar.app /Applications/
```

The app will preserve your preferences in `~/.ccusage-bar-prefs.json`.

## Configuration

### Runtime Configuration (via Menu)

All preferences are saved automatically to `~/.ccusage-bar-prefs.json`:

- **Refresh interval**: Click "Refresh interval" → Select 1min, 2min, 5min, or 10min
- **Section visibility**: Click "Show sections" → Toggle Projects/Daily/Weekly/Monthly
- **Week start day**: Click "Week starts on" → Choose Monday or Sunday
- **Start at Login**: Click "Start at Login" to toggle automatic startup

**Preferences file location**: `~/.ccusage-bar-prefs.json`

Example preferences file:
```json
{
  "refresh_interval": 300,
  "show_sections": {
    "session": true,
    "daily": true,
    "weekly": true,
    "monthly": false
  },
  "week_start_day": "monday"
}
```

### Build-Time Configuration

Edit `user_config.py` before building to customize defaults:

```python
# Show/hide sections (default state before user changes)
SHOW_SESSION = True   # Projects section
SHOW_DAILY = True
SHOW_WEEKLY = True
SHOW_MONTHLY = True

# Number of entries per section
SESSION_LIMIT = 5   # Top 5 projects shown, rest in "View all" submenu
DAILY_LIMIT = 7     # Last 7 days
WEEKLY_LIMIT = 4    # Last 4 weeks
MONTHLY_LIMIT = 6   # Last 6 months

# Default refresh interval in seconds (can be changed via menu)
DEFAULT_REFRESH_INTERVAL = 300  # 5 minutes

# Data fetch range (days to look back)
DAILY_SINCE_DAYS = 30    # Fetch last 30 days of daily data
WEEKLY_SINCE_DAYS = 60   # Fetch last 60 days for weekly grouping
MONTHLY_SINCE_DAYS = 180 # Fetch last 180 days for monthly grouping
SESSION_SINCE_DAYS = 30  # Fetch projects from last 30 days
```

After changing config, rebuild:
```bash
./build.sh
cp -r dist/ccusage-bar.app /Applications/
```

### Visual Customization

Edit `menu_formatter.py` to customize font sizes and colors:

```python
class MenuFormatter:
    # Font sizes (in points)
    FONT_SIZE_HEADER = 13.0   # Section headers (━━━ Cost ━━━)
    FONT_SIZE_LARGE = 12.0    # Currently unused
    FONT_SIZE_NORMAL = 11.0   # Labels, values, project names
    FONT_SIZE_SMALL = 10.0    # Token counts (secondary info)

    # Color threshold for high costs (in USD)
    threshold = 5.0  # Projects ≥$5.00 show in red
```

After changing formatting, rebuild:
```bash
./build.sh
cp -r dist/ccusage-bar.app /Applications/
```

### System Configuration

Edit `config.py` to change system paths:

```python
# Path to npx executable (used to run ccusage)
NPX_PATH = "/Users/yourusername/.nvm/versions/node/v25.0.0/bin/npx"

# Default refresh interval (seconds)
REFRESH_INTERVAL = 300  # Overridden by user_config.py
```

## Development

### Run without building:
```bash
python3 app.py
```

### Project Structure
```
ccusage-bar/
├── app.py              # Main rumps application
├── ccusage_client.py   # ccusage CLI wrapper
├── menu_formatter.py   # NSAttributedString formatting
├── config.py           # System config (npx path, etc.)
├── user_config.py      # User-editable configuration
├── preferences.py      # Preferences persistence
├── setup.py            # py2app bundling config
├── build.sh            # Build script
├── icon-44.png         # Menu bar icon (Retina)
└── requirements.txt    # Python dependencies
```

### Key Technical Details

- **rumps**: macOS menu bar framework via PyObjC
- **PyObjC**: NSAttributedString for rich text formatting
- **ccusage**: Claude Code CLI tool (via npx)
- **py2app**: Bundle as standalone .app
- **Threading**: Background data fetching and installation
- **JSON**: ccusage output parsing

## ccusage Data Schema

All four commands (`daily`, `weekly`, `monthly`, `session`) use the same JSON structure:

```json
{
  "daily": [
    { "date": "2026-02-07", "totalCost": 0.15, "totalTokens": 1234, ... }
  ],
  "totals": { "totalCost": 12.34, "totalTokens": 156789 }
}
```

**Note:** Despite what the ccusage docs say, `monthly` and `session` also use `totalCost`/`totals`, not `costUSD`/`summary`.

## Troubleshooting

### App doesn't start
- **Check Console.app** for crash logs: Open Console.app, search for "ccusage-bar"
- **Verify Python version**: `python3 --version` (need 3.12+)
- **Rebuild the app**: `./build.sh`
- **Check permissions**: App might be blocked by Gatekeeper - right-click and select "Open"

### "ccusage not found" or "⚠️ setup required"
- **Use auto-install**: Click "→ Install ccusage now" in the menu
- **Manual install**: `npm install -g ccusage`
- **Verify installation**: `npx ccusage --version`
- **Check npx path**: Verify NPX_PATH in `config.py` matches your Node.js installation
  ```bash
  which npx  # Should match NPX_PATH in config.py
  ```

### No data showing / Menu shows "(no data)"
- **Test ccusage manually**:
  ```bash
  npx ccusage daily --json
  ```
- **Check Claude Code data directories**:
  - `~/.claude/projects` - should contain .jsonl files
  - `~/Library/Application Support/21st-desktop/claude-sessions` - for 1code sessions
- **Check debug log**:
  ```bash
  tail -f ~/.ccusage-bar-debug.log
  ```
- **Try manual refresh**: Click "Refresh Now" in menu

### Menu bar shows "⚠️" warning indicator
- **Stuck state detected** - data fetch may have hung
- **Check debug log**: `cat ~/.ccusage-bar-debug.log`
- **Force refresh**: Click "Refresh Now"
- **Restart app**: Quit and relaunch
- **Check ccusage**: Run `npx ccusage daily --json` manually to verify it works

### Menu bar icon missing
- **Verify icon file**: Check that `icon-44.png` exists in project directory
- **Rebuild to include icon**: `./build.sh`
- **Check bundle contents**:
  ```bash
  ls -la dist/ccusage-bar.app/Contents/Resources/icon-44.png
  ```

### Formatting not showing (no bold, colors, or font sizes)
- **Use bundled app**: Run `open /Applications/ccusage-bar.app`, not `python3 app.py`
- **Check menu_formatter is bundled**:
  ```bash
  python3 -m zipfile -l dist/ccusage-bar.app/Contents/Resources/lib/python312.zip | grep menu_formatter
  ```
- **Rebuild if missing**: `./build.sh`

### "Start at Login" shows "approval needed"
- **Open System Settings**: Go to "General" → "Login Items"
- **Find ccusage-bar** in the list and enable it
- **Return to app** and the status should update

### Week dates seem wrong
- **Check week start preference**: Click "Week starts on" and verify Monday/Sunday setting
- **Understand the format**: ccusage uses ISO-style week grouping
  - Monday start: Week begins on Monday
  - Sunday start: Week begins on Sunday (not ISO standard)

### High CPU usage
- **Increase refresh interval**: Click "Refresh interval" → Select 5min or 10min
- **Disable unused sections**: Click "Show sections" → Uncheck sections you don't need
- **Check debug log**: Look for repeated errors in `~/.ccusage-bar-debug.log`

### Preferences not saving
- **Check file permissions**:
  ```bash
  ls -la ~/.ccusage-bar-prefs.json
  ```
- **Verify JSON is valid**:
  ```bash
  cat ~/.ccusage-bar-prefs.json | python3 -m json.tool
  ```
- **Delete and recreate**: Remove file and restart app to regenerate defaults
  ```bash
  rm ~/.ccusage-bar-prefs.json
  ```

## License

MIT

## Credits

- Built with [rumps](https://github.com/jaredks/rumps)
- Uses [ccusage](https://ccusage.com/) by Anthropic
- Icon from [Icons8](https://icons8.com)
