"""Database initialization and connection management."""

import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from .seed import DEFAULT_USER_ID, get_default_user_profile, get_default_watchlist_entries

# Thread-local storage for connections
_thread_local = threading.local()


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get or create a thread-local SQLite connection.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        SQLite connection with row factory set.
    """
    if not hasattr(_thread_local, "connection"):
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _thread_local.connection = conn
    return _thread_local.connection


def close_db_connection() -> None:
    """Close the thread-local database connection."""
    if hasattr(_thread_local, "connection"):
        _thread_local.connection.close()
        delattr(_thread_local, "connection")


def _schema_exists(conn: sqlite3.Connection) -> bool:
    """Check if database schema has been created.

    Args:
        conn: SQLite connection.

    Returns:
        True if at least one table exists, False otherwise.
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users_profile';"
    )
    return cursor.fetchone() is not None


def _create_schema(conn: sqlite3.Connection) -> None:
    """Create database schema from schema.sql.

    Args:
        conn: SQLite connection.
    """
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r") as f:
        schema = f.read()

    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()


def _seed_data(conn: sqlite3.Connection) -> None:
    """Insert default seed data.

    Args:
        conn: SQLite connection.
    """
    cursor = conn.cursor()

    # Insert default user profile if not exists
    cursor.execute(
        "SELECT id FROM users_profile WHERE id = ?",
        (DEFAULT_USER_ID,),
    )
    if cursor.fetchone() is None:
        user_data = get_default_user_profile()
        cursor.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (user_data["id"], user_data["cash_balance"], user_data["created_at"]),
        )

    # Insert default watchlist entries if not exists
    for entry in get_default_watchlist_entries():
        cursor.execute(
            "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
            (entry["user_id"], entry["ticker"]),
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (entry["id"], entry["user_id"], entry["ticker"], entry["added_at"]),
            )

    conn.commit()


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize SQLite database with schema and seed data.

    If the database file doesn't exist or tables are missing, creates the schema
    and seeds default data. This enables lazy initialization on first use.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        SQLite connection with row factory set.
    """
    # Ensure parent directory exists
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # Get or create connection
    conn = get_db_connection(db_path)

    # Create schema if missing
    if not _schema_exists(conn):
        _create_schema(conn)

    # Seed data
    _seed_data(conn)

    return conn


def execute_query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a SELECT query.

    Args:
        conn: SQLite connection.
        sql: SQL query string.
        params: Query parameters.

    Returns:
        List of rows as dictionaries.
    """
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


def execute_insert(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> None:
    """Execute an INSERT/UPDATE/DELETE statement and commit.

    Args:
        conn: SQLite connection.
        sql: SQL statement string.
        params: Statement parameters.
    """
    cursor = conn.cursor()
    cursor.execute(sql, params)
    conn.commit()


def execute_insert_many(conn: sqlite3.Connection, sql: str, params_list: list[tuple]) -> None:
    """Execute multiple INSERT/UPDATE/DELETE statements and commit.

    Args:
        conn: SQLite connection.
        sql: SQL statement string.
        params_list: List of parameter tuples.
    """
    cursor = conn.cursor()
    cursor.executemany(sql, params_list)
    conn.commit()


# Portfolio and position helpers


def get_positions(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> list[dict[str, Any]]:
    """Get all positions for a user.

    Args:
        conn: SQLite connection.
        user_id: User ID (default: "default").

    Returns:
        List of positions.
    """
    return execute_query(
        conn,
        "SELECT * FROM positions WHERE user_id = ? ORDER BY ticker",
        (user_id,),
    )


def get_position(
    conn: sqlite3.Connection, ticker: str, user_id: str = DEFAULT_USER_ID
) -> Optional[dict[str, Any]]:
    """Get a single position by ticker.

    Args:
        conn: SQLite connection.
        ticker: Ticker symbol.
        user_id: User ID (default: "default").

    Returns:
        Position dict or None if not found.
    """
    result = execute_query(
        conn,
        "SELECT * FROM positions WHERE user_id = ? AND ticker = ?",
        (user_id, ticker),
    )
    return result[0] if result else None


def get_user_profile(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> dict[str, Any]:
    """Get user profile.

    Args:
        conn: SQLite connection.
        user_id: User ID (default: "default").

    Returns:
        User profile dict.
    """
    result = execute_query(
        conn,
        "SELECT * FROM users_profile WHERE id = ?",
        (user_id,),
    )
    return result[0] if result else None


def get_watchlist(conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID) -> list[str]:
    """Get watchlist tickers for a user.

    Args:
        conn: SQLite connection.
        user_id: User ID (default: "default").

    Returns:
        List of ticker symbols.
    """
    result = execute_query(
        conn,
        "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY ticker",
        (user_id,),
    )
    return [row["ticker"] for row in result]


def get_trades(
    conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID, limit: int = 100
) -> list[dict[str, Any]]:
    """Get trade history for a user.

    Args:
        conn: SQLite connection.
        user_id: User ID (default: "default").
        limit: Maximum number of trades to return.

    Returns:
        List of trades ordered by execution time (newest first).
    """
    return execute_query(
        conn,
        "SELECT * FROM trades WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
        (user_id, limit),
    )


def get_portfolio_snapshots(
    conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID, limit: int = 1000
) -> list[dict[str, Any]]:
    """Get portfolio value snapshots for a user.

    Args:
        conn: SQLite connection.
        user_id: User ID (default: "default").
        limit: Maximum number of snapshots to return.

    Returns:
        List of snapshots ordered by time (oldest first).
    """
    return execute_query(
        conn,
        "SELECT * FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at ASC LIMIT ?",
        (user_id, limit),
    )


def get_chat_messages(
    conn: sqlite3.Connection, user_id: str = DEFAULT_USER_ID, limit: int = 100
) -> list[dict[str, Any]]:
    """Get chat message history for a user.

    Args:
        conn: SQLite connection.
        user_id: User ID (default: "default").
        limit: Maximum number of messages to return.

    Returns:
        List of messages ordered by creation time (oldest first).
    """
    return execute_query(
        conn,
        "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC LIMIT ?",
        (user_id, limit),
    )
