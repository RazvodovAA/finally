"""Tests for API routes."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import (
    DEFAULT_USER_ID,
    init_db,
    execute_insert,
    get_user_profile,
)
from app.market import PriceCache, MarketDataSource
from app.main import create_app
from app.routes import create_portfolio_router, create_watchlist_router
from app.routes.system import router as system_router


@pytest.fixture
def temp_db_path(tmp_path: Path) -> str:
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test.db")
    return db_path


@pytest.fixture
def test_conn(temp_db_path: str) -> sqlite3.Connection:
    """Create a test database connection."""
    conn = init_db(temp_db_path)
    yield conn
    conn.close()


@pytest.fixture
def price_cache() -> PriceCache:
    """Create a price cache with some test data."""
    cache = PriceCache()
    # Initialize with test prices for default watchlist tickers
    cache.update("AAPL", 150.0)
    cache.update("GOOGL", 140.0)
    cache.update("MSFT", 380.0)
    cache.update("AMZN", 170.0)
    cache.update("TSLA", 250.0)
    cache.update("NVDA", 875.0)
    cache.update("META", 520.0)
    cache.update("JPM", 190.0)
    cache.update("V", 290.0)
    cache.update("NFLX", 420.0)
    # Additional ticker for testing
    cache.update("PYPL", 65.0)
    return cache


@pytest.fixture
def mock_market_source() -> AsyncMock:
    """Create a mock market data source."""
    mock = AsyncMock(spec=MarketDataSource)
    mock.get_tickers.return_value = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
    return mock


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a test client with a temporary database."""
    # Create fresh price cache for this test
    fresh_cache = PriceCache()
    fresh_cache.update("AAPL", 150.0)
    fresh_cache.update("GOOGL", 140.0)
    fresh_cache.update("MSFT", 380.0)
    fresh_cache.update("AMZN", 170.0)
    fresh_cache.update("TSLA", 250.0)
    fresh_cache.update("NVDA", 875.0)
    fresh_cache.update("META", 520.0)
    fresh_cache.update("JPM", 190.0)
    fresh_cache.update("V", 290.0)
    fresh_cache.update("NFLX", 420.0)
    fresh_cache.update("PYPL", 65.0)

    # Create fresh temp database path for this test
    fresh_db_path = str(tmp_path / "test.db")

    with patch("app.main.create_market_data_source") as mock_create_source, \
         patch("app.main.PriceCache") as mock_cache_class:
        # Mock the market data source
        mock_source = MagicMock()
        mock_source.start = AsyncMock()
        mock_source.stop = AsyncMock()
        mock_source.add_ticker = AsyncMock()
        mock_source.remove_ticker = AsyncMock()
        # get_tickers is synchronous, not async
        mock_source.get_tickers = MagicMock(return_value=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"])
        mock_create_source.return_value = mock_source

        # Mock PriceCache to return our fresh test instance
        mock_cache_class.return_value = fresh_cache

        app = create_app(db_path=fresh_db_path)
        yield TestClient(app)


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check returns ok status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data


class TestPortfolioEndpoints:
    """Tests for portfolio endpoints."""

    def test_get_portfolio_empty(self, client: TestClient) -> None:
        """Test getting portfolio with no positions."""
        response = client.get("/api/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert data["positions"] == []
        assert data["cash_balance"] == 10000.0
        assert data["total_value"] == 10000.0
        assert data["total_unrealized_pnl"] == 0.0

    def test_buy_stock_success(self, client: TestClient) -> None:
        """Test successful buy order."""
        response = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Buy order executed" in data["message"]
        assert data["updated_portfolio"]["cash_balance"] == 10000.0 - (10 * 150.0)
        assert len(data["updated_portfolio"]["positions"]) == 1
        assert data["updated_portfolio"]["positions"][0]["ticker"] == "AAPL"
        assert data["updated_portfolio"]["positions"][0]["quantity"] == 10.0

    def test_buy_insufficient_cash(self, client: TestClient) -> None:
        """Test buy with insufficient cash."""
        # Try to buy more than we can afford
        response = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 100},
        )
        assert response.status_code == 422
        data = response.json()
        assert "Insufficient cash" in data["detail"]

    def test_buy_invalid_ticker(self, client: TestClient) -> None:
        """Test buy with no price available."""
        response = client.post(
            "/api/portfolio/trade",
            json={"ticker": "INVALID", "side": "buy", "quantity": 1},
        )
        assert response.status_code == 404
        data = response.json()
        assert "No price available" in data["detail"]

    def test_buy_negative_quantity(self, client: TestClient) -> None:
        """Test buy with negative quantity."""
        response = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": -1},
        )
        assert response.status_code == 400
        data = response.json()
        assert "quantity must be positive" in data["detail"]

    def test_sell_stock_success(self, client: TestClient) -> None:
        """Test successful sell order."""
        # First buy some stock
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )

        # Then sell some
        response = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "sell", "quantity": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Sell order executed" in data["message"]
        assert len(data["updated_portfolio"]["positions"]) == 1
        assert data["updated_portfolio"]["positions"][0]["quantity"] == 5.0

    def test_sell_insufficient_shares(self, client: TestClient) -> None:
        """Test sell with insufficient shares."""
        response = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "sell", "quantity": 1},
        )
        assert response.status_code == 422
        data = response.json()
        assert "No position" in data["detail"] or "Insufficient shares" in data["detail"]

    def test_sell_all_shares_removes_position(self, client: TestClient) -> None:
        """Test that selling all shares removes the position."""
        # Buy some stock
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )

        # Sell all
        response = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "sell", "quantity": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["updated_portfolio"]["positions"]) == 0

    def test_portfolio_value_calculation(self, client: TestClient) -> None:
        """Test portfolio total value calculation."""
        # Buy 10 AAPL at 150 = 1500
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )

        response = client.get("/api/portfolio")
        data = response.json()
        expected_value = 10000.0 - 1500.0 + (10 * 150.0)
        assert data["total_value"] == expected_value

    def test_unrealized_pnl_calculation(self, client: TestClient, client_app: TestClient = None) -> None:
        """Test unrealized P&L calculation."""
        # Buy 10 AAPL at 150
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )

        # Update price in cache to 155
        client.app.state.price_cache.update("AAPL", 155.0)

        response = client.get("/api/portfolio")
        data = response.json()
        position = data["positions"][0]
        assert position["current_price"] == 155.0
        assert position["avg_cost"] == 150.0
        assert position["unrealized_pnl"] == 50.0  # 10 * (155 - 150)
        assert position["pnl_percent"] == 3.33

    def test_invalid_trade_side(self, client: TestClient) -> None:
        """Test trade with invalid side."""
        response = client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "hold", "quantity": 1},
        )
        assert response.status_code == 400
        data = response.json()
        assert "side must be" in data["detail"]

    def test_get_portfolio_history(self, client: TestClient) -> None:
        """Test getting portfolio history."""
        response = client.get("/api/portfolio/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_portfolio_snapshot_on_trade(self, client: TestClient) -> None:
        """Test that portfolio snapshot is created on trade."""
        conn = client.app.state.db_connection
        # Get initial snapshot count
        initial_snapshots = conn.execute(
            "SELECT COUNT(*) as count FROM portfolio_snapshots WHERE user_id = ?",
            (DEFAULT_USER_ID,),
        ).fetchone()
        initial_count = initial_snapshots["count"] if initial_snapshots else 0

        # Execute a trade
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 1},
        )

        # Check new snapshot was created
        new_snapshots = conn.execute(
            "SELECT COUNT(*) as count FROM portfolio_snapshots WHERE user_id = ?",
            (DEFAULT_USER_ID,),
        ).fetchone()
        new_count = new_snapshots["count"] if new_snapshots else 0
        assert new_count > initial_count


class TestWatchlistEndpoints:
    """Tests for watchlist endpoints."""

    def test_get_watchlist(self, client: TestClient) -> None:
        """Test getting current watchlist."""
        response = client.get("/api/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have default watchlist
        tickers = {item["ticker"] for item in data}
        assert "AAPL" in tickers
        assert "GOOGL" in tickers

    def test_watchlist_includes_prices(self, client: TestClient) -> None:
        """Test that watchlist items include price data."""
        response = client.get("/api/watchlist")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        item = data[0]
        assert "ticker" in item
        assert "price" in item
        assert "change" in item
        assert "change_percent" in item
        assert "direction" in item

    def test_add_to_watchlist(self, client: TestClient) -> None:
        """Test adding a ticker to watchlist."""
        response = client.post(
            "/api/watchlist",
            json={"ticker": "TSLA"},
        )
        assert response.status_code == 200
        data = response.json()
        tickers = {item["ticker"] for item in data}
        assert "TSLA" in tickers

    def test_add_duplicate_ticker(self, client: TestClient) -> None:
        """Test adding a ticker that's already in watchlist."""
        # AAPL is in default watchlist
        response = client.post(
            "/api/watchlist",
            json={"ticker": "AAPL"},
        )
        assert response.status_code == 200
        data = response.json()
        # Should not duplicate
        aapl_count = sum(1 for item in data if item["ticker"] == "AAPL")
        assert aapl_count == 1

    def test_remove_from_watchlist(self, client: TestClient) -> None:
        """Test removing ticker from watchlist."""
        response = client.delete("/api/watchlist/NFLX")
        assert response.status_code == 200
        data = response.json()
        tickers = {item["ticker"] for item in data}
        assert "NFLX" not in tickers

    def test_ticker_case_insensitive(self, client: TestClient) -> None:
        """Test that ticker symbols are case-insensitive."""
        response = client.post(
            "/api/watchlist",
            json={"ticker": "pypl"},
        )
        assert response.status_code == 200
        data = response.json()
        tickers = {item["ticker"] for item in data}
        assert "PYPL" in tickers


class TestIntegration:
    """Integration tests for multiple endpoints working together."""

    def test_buy_adds_position(self, client: TestClient) -> None:
        """Test that buying adds a position to portfolio."""
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "GOOGL", "side": "buy", "quantity": 5},
        )

        response = client.get("/api/portfolio")
        data = response.json()
        googl_position = next((p for p in data["positions"] if p["ticker"] == "GOOGL"), None)
        assert googl_position is not None
        assert googl_position["quantity"] == 5
        assert googl_position["avg_cost"] == 140.0

    def test_average_cost_multiple_buys(self, client: TestClient) -> None:
        """Test that average cost is correctly calculated on multiple buys."""
        # Buy 10 at 150
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )

        # Update price and buy more at 160
        client.app.state.price_cache.update("AAPL", 160.0)
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )

        response = client.get("/api/portfolio")
        data = response.json()
        position = next((p for p in data["positions"] if p["ticker"] == "AAPL"), None)
        assert position is not None
        # Avg cost should be (150*10 + 160*10) / 20 = 155
        assert position["avg_cost"] == 155.0
        assert position["quantity"] == 20.0

    def test_cash_balance_updates(self, client: TestClient) -> None:
        """Test cash balance updates correctly."""
        initial = client.get("/api/portfolio").json()["cash_balance"]

        # Buy 10 AAPL at 150
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 10},
        )
        after_buy = client.get("/api/portfolio").json()["cash_balance"]
        assert after_buy == initial - 1500.0

        # Sell 5 AAPL at 150
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "sell", "quantity": 5},
        )
        after_sell = client.get("/api/portfolio").json()["cash_balance"]
        assert after_sell == after_buy + 750.0

    def test_trade_history_recorded(self, client: TestClient) -> None:
        """Test that trades are recorded in history."""
        client.post(
            "/api/portfolio/trade",
            json={"ticker": "AAPL", "side": "buy", "quantity": 5},
        )

        conn = client.app.state.db_connection
        trades = conn.execute(
            "SELECT * FROM trades WHERE user_id = ? AND ticker = ?",
            (DEFAULT_USER_ID, "AAPL"),
        ).fetchall()
        assert len(trades) > 0
        trade = trades[0]
        assert trade["side"] == "buy"
        assert trade["quantity"] == 5
        assert trade["price"] == 150.0
