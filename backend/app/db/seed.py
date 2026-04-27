"""Seed data and default values for FinAlly database."""

from datetime import datetime, timezone
from uuid import uuid4

# Default user ID
DEFAULT_USER_ID = "default"

# Default cash balance
DEFAULT_CASH_BALANCE = 10000.0

# Default watchlist tickers
DEFAULT_WATCHLIST = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
]


def get_default_user_profile():
    """Get default user profile data."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": DEFAULT_USER_ID,
        "cash_balance": DEFAULT_CASH_BALANCE,
        "created_at": now,
    }


def get_default_watchlist_entries():
    """Get default watchlist entries."""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": str(uuid4()),
            "user_id": DEFAULT_USER_ID,
            "ticker": ticker,
            "added_at": now,
        }
        for ticker in DEFAULT_WATCHLIST
    ]
