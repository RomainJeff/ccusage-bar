# User configuration for ccusage-bar

# Which sections to display in the menu (set to False to hide)
SHOW_SESSION = True
SHOW_DAILY = True
SHOW_WEEKLY = True
SHOW_MONTHLY = True

# Number of entries to show per section (not including the Total line)
SESSION_LIMIT = 5  # Last N sessions
DAILY_LIMIT = 7    # Last N days
WEEKLY_LIMIT = 4   # Last N weeks
MONTHLY_LIMIT = 6  # Last N months

# Default refresh interval in seconds (can be changed in the menu)
DEFAULT_REFRESH_INTERVAL = 300  # 5 minutes

# Date range for fetching data (days back from today)
DAILY_SINCE_DAYS = 30
WEEKLY_SINCE_DAYS = 60
MONTHLY_SINCE_DAYS = 180
SESSION_SINCE_DAYS = 30
