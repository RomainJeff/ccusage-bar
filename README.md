# ccusage-bar

macOS menu bar app showing Claude Code usage costs in USD.

![Claude Code icon in menu bar](icon-44.png)

## Features

### 📊 **Visual Hierarchy**
- **NSAttributedString formatting** with multiple font sizes (13pt headers, 11pt normal, 10pt secondary info)
- **Bold labels** for section headers and cost summaries
- **Color-coded alerts** for high-cost projects (≥$5.00 in red)
- **Retina-ready Claude icon** (44x44) in menu bar

### 💰 **Usage Tracking**
- **Today's cost** displayed in menu bar next to icon
- **Four data views**: Cost summary, Projects, Daily, Weekly, Monthly
- **Relative date labels**: "Today", "Yesterday", "This week", "Last week", etc.
- **Token counts** with compact formatting (1.2M, 15K, etc.)

### 🔄 **Smart Refresh**
- **Auto-refresh** with configurable intervals (1min, 2min, 5min, 10min)
- **"X minutes ago"** relative refresh time display
- **Manual refresh** button in menu

### ⚙️ **Configuration**
- **Persistent preferences** saved to `~/.ccusage-bar-prefs.json`
- **Toggle sections** on/off (Projects, Daily, Weekly, Monthly)
- **Customizable refresh interval** via menu
- Reads data from both `~/.claude` and 1code sessions

### 🚀 **Auto-Installation**
- **Automatic ccusage detection** on startup
- **One-click installation** if ccusage not found
- Runs `npm install -g ccusage` in background
- Shows installation progress in menu bar

## Screenshots

**Normal view:**
```
━━━ Cost ━━━
Today: $0.15 · 1.2K tokens
Last 30 days: $12.34 · 156K tokens

━━━ Projects ━━━
/path/to/project1: $5.67 · 45K    [in red if ≥$5]
/path/to/project2: $2.34 · 12K
→ View all projects

━━━ Daily ━━━
Today: $0.15 · 1.2K tokens
Yesterday: $0.89 · 8K tokens
2026-02-05: $1.23 · 10K tokens

Last refresh: 2 minutes ago
```

**Setup view (ccusage not installed):**
```
⚠️ setup required

━━━ ccusage not found ━━━
ccusage is required but not installed

→ Install ccusage now  [clickable]

Manual install: npm install -g ccusage
```

## Installation

### Prerequisites
- macOS (tested on macOS 11+)
- Python 3.12+ with PyObjC
- Node.js and npm (for ccusage)

### Build and Install

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd ccusage-bar
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Build the app:**
   ```bash
   ./build.sh
   ```

4. **Copy to Applications:**
   ```bash
   cp -r dist/ccusage-bar.app /Applications/
   ```

5. **Launch:**
   - Open from Applications folder, or
   - Add to Login Items for auto-start

### ccusage Installation

The app will automatically detect if `ccusage` is not installed and offer to install it via the menu. Alternatively, install manually:

```bash
npm install -g ccusage
```

## Configuration

### Runtime Configuration (via Menu)

All preferences are saved automatically to `~/.ccusage-bar-prefs.json`:

- **Refresh interval**: Click "Refresh interval" → Select 1min, 2min, 5min, or 10min
- **Section visibility**: Click "Show sections" → Toggle Projects/Daily/Weekly/Monthly

### Build-Time Configuration

Edit `user_config.py` before building to customize:

```python
# Show/hide sections (default state)
SHOW_SESSION = True   # Projects section
SHOW_DAILY = True
SHOW_WEEKLY = True
SHOW_MONTHLY = True

# Number of entries per section
SESSION_LIMIT = 5   # Top 5 projects, rest in "View all" submenu
DAILY_LIMIT = 7     # Last 7 days
WEEKLY_LIMIT = 4    # Last 4 weeks
MONTHLY_LIMIT = 6   # Last 6 months

# Data fetch range (days to look back)
DAILY_SINCE_DAYS = 30
WEEKLY_SINCE_DAYS = 60
MONTHLY_SINCE_DAYS = 180
SESSION_SINCE_DAYS = 30
```

After changing config, rebuild:
```bash
./build.sh
```

### Visual Customization

Edit `menu_formatter.py` to customize font sizes and colors:

```python
class MenuFormatter:
    # Font sizes (in points)
    FONT_SIZE_HEADER = 13.0   # Section headers
    FONT_SIZE_LARGE = 12.0    # Important values
    FONT_SIZE_NORMAL = 11.0   # Regular items
    FONT_SIZE_SMALL = 10.0    # Token counts

    # Color threshold for high costs (in USD)
    threshold = 5.0  # Projects ≥$5 show in red
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
- Check Console.app for crash logs
- Verify Python 3.12+ is installed: `python3 --version`
- Rebuild: `./build.sh`

### "ccusage not found" error
- Click "→ Install ccusage now" in the menu, or
- Install manually: `npm install -g ccusage`
- Verify: `npx ccusage --version`

### No data showing
- Run ccusage manually to verify it works: `npx ccusage daily --json`
- Check that `~/.claude/projects` exists and has .jsonl files
- For 1code sessions, check `~/Library/Application Support/21st-desktop/claude-sessions`

### Menu bar icon missing
- Verify `icon-44.png` exists in project directory
- Rebuild to include icon: `./build.sh`

### Formatting not showing
- Verify you're running the bundled app, not `python3 app.py` directly
- Check that `menu_formatter.pyc` is in the bundle:
  ```bash
  python3 -m zipfile -l dist/ccusage-bar.app/Contents/Resources/lib/python312.zip | grep menu_formatter
  ```

## License

MIT

## Credits

- Built with [rumps](https://github.com/jaredks/rumps)
- Uses [ccusage](https://github.com/anthropics/ccusage) by Anthropic
- Icon from [Icons8](https://icons8.com)
