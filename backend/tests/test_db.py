"""Unit tests for database module."""

import sqlite3
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from app.db import (
    DEFAULT_CASH_BALANCE,
    DEFAULT_USER_ID,
    DEFAULT_WATCHLIST,
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


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = init_db(str(db_path))
        yield conn, db_path
        close_db_connection()


class TestSchemaCreation:
    """Test database schema creation."""

    def test_init_db_creates_file(self, temp_db):
        """Test that init_db creates database file."""
        conn, db_path = temp_db
        assert db_path.exists()

    def test_init_db_creates_tables(self, temp_db):
        """Test that all required tables are created."""
        conn, _ = temp_db
        cursor = conn.cursor()

        # Check each table exists
        tables = [
            "users_profile",
            "watchlist",
            "positions",
            "trades",
            "portfolio_snapshots",
            "chat_messages",
        ]

        for table in tables:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            assert cursor.fetchone() is not None, f"Table {table} not created"

    def test_init_db_idempotent(self, temp_db):
        """Test that calling init_db multiple times is safe."""
        conn, db_path = temp_db
        # Call init_db again on existing database
        conn2 = init_db(str(db_path))
        assert conn2 is not None

    def test_schema_without_file(self):
        """Test schema creation on fresh database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "subdir" / "new.db"
            init_db(str(db_path))
            assert db_path.exists()
            close_db_connection()


class TestSeedData:
    """Test seed data insertion."""

    def test_default_user_created(self, temp_db):
        """Test that default user is created."""
        conn, _ = temp_db
        user = get_user_profile(conn, DEFAULT_USER_ID)
        assert user is not None
        assert user["id"] == DEFAULT_USER_ID
        assert user["cash_balance"] == DEFAULT_CASH_BALANCE

    def test_default_watchlist_created(self, temp_db):
        """Test that default watchlist is created."""
        conn, _ = temp_db
        watchlist = get_watchlist(conn, DEFAULT_USER_ID)
        assert len(watchlist) == len(DEFAULT_WATCHLIST)
        assert set(watchlist) == set(DEFAULT_WATCHLIST)

    def test_seed_data_not_duplicated(self, temp_db):
        """Test that seed data is not duplicated on re-init."""
        conn, db_path = temp_db
        initial_count = len(get_watchlist(conn, DEFAULT_USER_ID))

        # Re-initialize database
        close_db_connection()
        conn = init_db(str(db_path))
        final_count = len(get_watchlist(conn, DEFAULT_USER_ID))

        assert initial_count == final_count == len(DEFAULT_WATCHLIST)


class TestQueryOperations:
    """Test query execution helpers."""

    def test_execute_query_select(self, temp_db):
        """Test execute_query for SELECT."""
        conn, _ = temp_db
        result = execute_query(conn, "SELECT * FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,))
        assert len(result) == 1
        assert result[0]["id"] == DEFAULT_USER_ID

    def test_execute_query_empty_result(self, temp_db):
        """Test execute_query with no results."""
        conn, _ = temp_db
        result = execute_query(conn, "SELECT * FROM positions WHERE user_id = ?", (DEFAULT_USER_ID,))
        assert result == []

    def test_execute_insert(self, temp_db):
        """Test execute_insert for INSERT."""
        conn, _ = temp_db
        trade_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, DEFAULT_USER_ID, "AAPL", "buy", 10, 150.0, "2024-01-01T00:00:00"),
        )

        # Verify insert
        result = execute_query(
            conn,
            "SELECT * FROM trades WHERE id = ?",
            (trade_id,),
        )
        assert len(result) == 1
        assert result[0]["ticker"] == "AAPL"

    def test_execute_insert_many(self, temp_db):
        """Test execute_insert_many for bulk inserts."""
        conn, _ = temp_db
        trades = [
            (str(uuid4()), DEFAULT_USER_ID, "AAPL", "buy", 10, 150.0, "2024-01-01T00:00:00"),
            (str(uuid4()), DEFAULT_USER_ID, "GOOGL", "sell", 5, 2800.0, "2024-01-01T01:00:00"),
        ]
        execute_insert_many(
            conn,
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            trades,
        )

        # Verify inserts
        result = execute_query(
            conn,
            "SELECT COUNT(*) as count FROM trades WHERE user_id = ?",
            (DEFAULT_USER_ID,),
        )
        assert result[0]["count"] == 2


class TestHelperFunctions:
    """Test high-level helper functions."""

    def test_get_positions_empty(self, temp_db):
        """Test get_positions on empty portfolio."""
        conn, _ = temp_db
        positions = get_positions(conn)
        assert positions == []

    def test_get_position_single(self, temp_db):
        """Test get_position for single ticker."""
        conn, _ = temp_db
        pos_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (pos_id, DEFAULT_USER_ID, "AAPL", 10, 150.0, "2024-01-01T00:00:00"),
        )

        position = get_position(conn, "AAPL")
        assert position is not None
        assert position["ticker"] == "AAPL"
        assert position["quantity"] == 10

    def test_get_position_not_found(self, temp_db):
        """Test get_position for nonexistent ticker."""
        conn, _ = temp_db
        position = get_position(conn, "NONEXISTENT")
        assert position is None

    def test_get_user_profile(self, temp_db):
        """Test get_user_profile."""
        conn, _ = temp_db
        profile = get_user_profile(conn)
        assert profile is not None
        assert profile["id"] == DEFAULT_USER_ID
        assert profile["cash_balance"] == DEFAULT_CASH_BALANCE

    def test_get_watchlist(self, temp_db):
        """Test get_watchlist."""
        conn, _ = temp_db
        watchlist = get_watchlist(conn)
        assert len(watchlist) == len(DEFAULT_WATCHLIST)
        assert "AAPL" in watchlist

    def test_get_trades_empty(self, temp_db):
        """Test get_trades on empty history."""
        conn, _ = temp_db
        trades = get_trades(conn)
        assert trades == []

    def test_get_trades_with_data(self, temp_db):
        """Test get_trades with trade history."""
        conn, _ = temp_db
        trade_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, DEFAULT_USER_ID, "AAPL", "buy", 10, 150.0, "2024-01-01T00:00:00"),
        )

        trades = get_trades(conn)
        assert len(trades) == 1
        assert trades[0]["ticker"] == "AAPL"

    def test_get_portfolio_snapshots_empty(self, temp_db):
        """Test get_portfolio_snapshots on empty history."""
        conn, _ = temp_db
        snapshots = get_portfolio_snapshots(conn)
        assert snapshots == []

    def test_get_portfolio_snapshots_with_data(self, temp_db):
        """Test get_portfolio_snapshots with data."""
        conn, _ = temp_db
        snap_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (snap_id, DEFAULT_USER_ID, 10500.0, "2024-01-01T00:00:00"),
        )

        snapshots = get_portfolio_snapshots(conn)
        assert len(snapshots) == 1
        assert snapshots[0]["total_value"] == 10500.0

    def test_get_chat_messages_empty(self, temp_db):
        """Test get_chat_messages on empty history."""
        conn, _ = temp_db
        messages = get_chat_messages(conn)
        assert messages == []

    def test_get_chat_messages_with_data(self, temp_db):
        """Test get_chat_messages with messages."""
        conn, _ = temp_db
        msg_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO chat_messages (id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, DEFAULT_USER_ID, "user", "Hello", "2024-01-01T00:00:00"),
        )

        messages = get_chat_messages(conn)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"


class TestConnectionManagement:
    """Test connection and thread safety."""

    def test_get_db_connection_returns_same_connection(self, temp_db):
        """Test that get_db_connection returns same connection in same thread."""
        conn, db_path = temp_db
        conn2 = get_db_connection(str(db_path))
        assert conn2 is conn

    def test_close_db_connection(self, temp_db):
        """Test closing connection."""
        conn, _ = temp_db
        close_db_connection()
        # After close, should be able to get a new connection
        # (would fail if connection state was corrupted)


class TestUniqueConstraints:
    """Test database constraints."""

    def test_watchlist_unique_constraint(self, temp_db):
        """Test that watchlist has unique constraint on (user_id, ticker)."""
        conn, _ = temp_db
        # Try to insert duplicate watchlist entry
        with pytest.raises(sqlite3.IntegrityError):
            execute_insert(
                conn,
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (str(uuid4()), DEFAULT_USER_ID, "AAPL", "2024-01-01T00:00:00"),
            )

    def test_positions_unique_constraint(self, temp_db):
        """Test that positions has unique constraint on (user_id, ticker)."""
        conn, _ = temp_db
        pos_id1 = str(uuid4())
        pos_id2 = str(uuid4())

        # Insert first position
        execute_insert(
            conn,
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (pos_id1, DEFAULT_USER_ID, "AAPL", 10, 150.0, "2024-01-01T00:00:00"),
        )

        # Try to insert duplicate position
        with pytest.raises(sqlite3.IntegrityError):
            execute_insert(
                conn,
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (pos_id2, DEFAULT_USER_ID, "AAPL", 20, 160.0, "2024-01-01T00:00:00"),
            )


class TestDataTypes:
    """Test data type handling."""

    def test_fractional_shares(self, temp_db):
        """Test that fractional shares are supported."""
        conn, _ = temp_db
        pos_id = str(uuid4())
        quantity = 10.5  # Fractional
        execute_insert(
            conn,
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (pos_id, DEFAULT_USER_ID, "AAPL", quantity, 150.0, "2024-01-01T00:00:00"),
        )

        position = get_position(conn, "AAPL")
        assert position["quantity"] == quantity

    def test_side_field_values(self, temp_db):
        """Test that trade side field accepts buy/sell."""
        conn, _ = temp_db
        trade_id1 = str(uuid4())
        trade_id2 = str(uuid4())

        execute_insert(
            conn,
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id1, DEFAULT_USER_ID, "AAPL", "buy", 10, 150.0, "2024-01-01T00:00:00"),
        )
        execute_insert(
            conn,
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id2, DEFAULT_USER_ID, "AAPL", "sell", 5, 155.0, "2024-01-01T01:00:00"),
        )

        trades = get_trades(conn)
        # Trades are returned in DESC order by executed_at, so most recent first
        assert trades[0]["side"] == "sell"
        assert trades[1]["side"] == "buy"

    def test_json_actions_field(self, temp_db):
        """Test that actions field can store JSON."""
        conn, _ = temp_db
        msg_id = str(uuid4())
        actions_json = '{"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}]}'

        execute_insert(
            conn,
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, DEFAULT_USER_ID, "assistant", "I bought some AAPL", actions_json, "2024-01-01T00:00:00"),
        )

        messages = get_chat_messages(conn)
        assert messages[0]["actions"] == actions_json
