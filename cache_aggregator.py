"""Aggregate cached daily rows into weekly/monthly structures.

Reconstructs the same JSON format that ccusage CLI returns for weekly
and monthly subcommands, so app.py sees no difference.
"""

from datetime import date, timedelta
from collections import defaultdict


def _week_start(d, week_start_day):
    """Return the week-start date for a given date."""
    if isinstance(d, str):
        d = date.fromisoformat(d)
    if week_start_day == "monday":
        return d - timedelta(days=d.weekday())
    else:  # sunday
        return d - timedelta(days=(d.weekday() + 1) % 7)


def _compute_totals(entries):
    total_cost = sum(e.get("totalCost", 0.0) for e in entries)
    total_tokens = sum(e.get("totalTokens", 0) for e in entries)
    return {"totalCost": total_cost, "totalTokens": total_tokens}


def build_daily_response(entries):
    return {"daily": entries, "totals": _compute_totals(entries)}


def build_weekly_response(entries, week_start_day="monday"):
    weeks = defaultdict(lambda: {"totalCost": 0.0, "totalTokens": 0})
    for entry in entries:
        ws = _week_start(entry["date"], week_start_day).isoformat()
        weeks[ws]["totalCost"] += entry.get("totalCost", 0.0)
        weeks[ws]["totalTokens"] += entry.get("totalTokens", 0)

    weekly = [
        {"week": ws, "totalCost": d["totalCost"], "totalTokens": d["totalTokens"]}
        for ws, d in sorted(weeks.items())
    ]
    return {"weekly": weekly, "totals": _compute_totals(entries)}


def build_monthly_response(entries):
    months = defaultdict(lambda: {"totalCost": 0.0, "totalTokens": 0})
    for entry in entries:
        month = entry["date"][:7]  # YYYY-MM
        months[month]["totalCost"] += entry.get("totalCost", 0.0)
        months[month]["totalTokens"] += entry.get("totalTokens", 0)

    monthly = [
        {"month": m, "totalCost": d["totalCost"], "totalTokens": d["totalTokens"]}
        for m, d in sorted(months.items())
    ]
    return {"monthly": monthly, "totals": _compute_totals(entries)}
