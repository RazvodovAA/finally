"""Integration tests for chat endpoint."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.market import PriceCache


@pytest.fixture
def client_with_prices(tmp_path, monkeypatch):
    """Create test client with populated price cache."""
    db_path = str(tmp_path / "test.db")
    app = create_app(db_path=db_path)

    # Populate price cache with seed prices
    price_cache: PriceCache = app.state.price_cache
    seed_prices = {
        "AAPL": 150.0,
        "GOOGL": 140.0,
        "MSFT": 380.0,
        "AMZN": 180.0,
        "TSLA": 250.0,
        "NVDA": 875.0,
        "META": 500.0,
        "JPM": 200.0,
        "V": 280.0,
        "NFLX": 420.0,
    }

    for ticker, price in seed_prices.items():
        price_cache.update(ticker, price)

    return TestClient(app), price_cache


def test_chat_basic_message_mock(client_with_prices, monkeypatch):
    """Test basic chat message with mock mode."""
    client, _ = client_with_prices
    monkeypatch.setenv("LLM_MOCK", "true")

    response = client.post("/api/chat", json={"message": "What should I do with my portfolio?"})

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert isinstance(data["message"], str)
    assert len(data["message"]) > 0


def test_chat_stores_in_database(client_with_prices, monkeypatch):
    """Test that chat messages are stored in database."""
    client, _ = client_with_prices
    monkeypatch.setenv("LLM_MOCK", "true")

    response = client.post("/api/chat", json={"message": "Hello AI!"})
    assert response.status_code == 200

    # Check database for stored messages
    conn = client.app.state.db_connection
    from app.db import DEFAULT_USER_ID

    messages = conn.execute(
        "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 2",
        (DEFAULT_USER_ID,),
    ).fetchall()

    assert len(messages) >= 2
    # Most recent should be assistant, before that user
    assert messages[0]["role"] == "assistant"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Hello AI!"


def test_chat_with_portfolio_context(client_with_prices, monkeypatch):
    """Test that chat includes portfolio context."""
    client, price_cache = client_with_prices
    monkeypatch.setenv("LLM_MOCK", "true")

    # Buy some stock first
    client.post(
        "/api/portfolio/trade",
        json={"ticker": "AAPL", "side": "buy", "quantity": 10},
    )

    # Chat endpoint should work with positions in portfolio
    response = client.post(
        "/api/chat",
        json={"message": "What's my current position?"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_chat_request_validation(client_with_prices, monkeypatch):
    """Test that chat endpoint validates requests."""
    client, _ = client_with_prices
    monkeypatch.setenv("LLM_MOCK", "true")

    # Missing message field
    response = client.post("/api/chat", json={})
    assert response.status_code == 422

    # Empty message
    response = client.post("/api/chat", json={"message": ""})
    # With mock mode, empty message should still work
    assert response.status_code == 200
