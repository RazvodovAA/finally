"""Database module for FinAlly backend."""

from .init import (
    close_db_connection,
    execute_insert,
    execute_insert_many,
    execute_query,
    get_chat_messages,
    get_db_connection,
    get_portfolio_snapshots,
    get_position,
    get_positions,
    get_trades,
    get_user_profile,
    get_watchlist,
    init_db,
)
from .seed import DEFAULT_CASH_BALANCE, DEFAULT_USER_ID, DEFAULT_WATCHLIST

__all__ = [
    "init_db",
    "get_db_connection",
    "close_db_connection",
    "execute_query",
    "execute_insert",
    "execute_insert_many",
    "get_positions",
    "get_position",
    "get_user_profile",
    "get_watchlist",
    "get_trades",
    "get_portfolio_snapshots",
    "get_chat_messages",
    "DEFAULT_USER_ID",
    "DEFAULT_CASH_BALANCE",
    "DEFAULT_WATCHLIST",
]
