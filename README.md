# ccusage-bar

macOS menu bar app showing Claude Code usage costs in USD.

## Features

- **Menu bar icon** showing today's total cost
- **Session, Daily, Weekly, Monthly** usage sections
- Auto-refresh (configurable interval: 1min, 2min, 5min, 10min)
- Reads data from both `~/.claude` and 1code sessions

## Installation

1. Build the app:
   ```bash
   ./build.sh
   ```

2. Copy to Applications:
   ```bash
   cp -r dist/ccusage-bar.app /Applications/
   ```

3. Launch from Applications or add to Login Items

## Configuration

Edit `user_config.py` to customize:

```python
# Show/hide sections
SHOW_SESSION = True
SHOW_DAILY = True
SHOW_WEEKLY = True
SHOW_MONTHLY = False  # Hide monthly view

# Number of entries per section
SESSION_LIMIT = 5  # Show last 5 sessions
DAILY_LIMIT = 7    # Show last 7 days
WEEKLY_LIMIT = 4   # Show last 4 weeks
MONTHLY_LIMIT = 6  # Show last 6 months

# Default refresh interval (seconds)
DEFAULT_REFRESH_INTERVAL = 300  # 5 minutes

# Data fetch range (days back)
DAILY_SINCE_DAYS = 30
WEEKLY_SINCE_DAYS = 60
MONTHLY_SINCE_DAYS = 180
SESSION_SINCE_DAYS = 30
```

After changing the config, rebuild:
```bash
./build.sh
```

## Development

Run without building:
```bash
python3 app.py
```

## Requirements

- Python 3.12+
- Node.js (for `npx ccusage`)
- macOS

## Files

- `app.py` — Main menu bar app
- `ccusage_client.py` — Wrapper for `ccusage` CLI
- `config.py` — System config (npx path, etc.)
- `user_config.py` — **User-editable configuration**
- `build.sh` — Build script for creating `.app` bundle
