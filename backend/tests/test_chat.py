"""Tests for chat endpoint."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import DEFAULT_USER_ID, execute_insert, init_db
from app.llm import ChatResponse, Trade, WatchlistChange, _get_mock_response
from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with test database."""
    db_path = str(tmp_path / "test.db")
    # Create a new app instance for each test with isolated database
    app = create_app(db_path=db_path)
    return TestClient(app)


def test_chat_endpoint_exists(client):
    """Test that /api/chat endpoint exists."""
    response = client.post("/api/chat", json={"message": "Hello"})
    # Will fail with error if LLM_MOCK not set, but at least the endpoint exists
    assert response.status_code in (200, 500)


def test_chat_with_mock_mode(client, monkeypatch):
    """Test chat with LLM_MOCK=true."""
    monkeypatch.setenv("LLM_MOCK", "true")

    response = client.post("/api/chat", json={"message": "What should I do?"})
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "trades" in data
    assert "watchlist_changes" in data
    assert isinstance(data["message"], str)
    assert isinstance(data["trades"], list)
    assert isinstance(data["watchlist_changes"], list)


def test_mock_response_structure():
    """Test that mock response has valid structure."""
    response = _get_mock_response()
    assert isinstance(response, ChatResponse)
    assert response.message
    assert isinstance(response.trades, list)
    assert isinstance(response.watchlist_changes, list)


def test_chat_response_model():
    """Test ChatResponse Pydantic model."""
    # Valid response with all fields
    resp = ChatResponse(
        message="Test message",
        trades=[Trade(ticker="AAPL", side="buy", quantity=10)],
        watchlist_changes=[WatchlistChange(ticker="GOOGL", action="add")],
    )
    assert resp.message == "Test message"
    assert len(resp.trades) == 1
    assert len(resp.watchlist_changes) == 1

    # Minimal response (only message required)
    resp2 = ChatResponse(message="Just a message")
    assert resp2.message == "Just a message"
    assert resp2.trades == []
    assert resp2.watchlist_changes == []


def test_trade_model():
    """Test Trade model validation."""
    trade = Trade(ticker="AAPL", side="buy", quantity=10)
    assert trade.ticker == "AAPL"
    assert trade.side == "buy"
    assert trade.quantity == 10


def test_watchlist_change_model():
    """Test WatchlistChange model validation."""
    change = WatchlistChange(ticker="GOOGL", action="add")
    assert change.ticker == "GOOGL"
    assert change.action == "add"
