"""Watchlist management endpoints."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import DEFAULT_USER_ID, execute_insert, get_watchlist, execute_query
from app.market import MarketDataSource, PriceCache

logger = logging.getLogger(__name__)


class WatchlistItem(BaseModel):
    """A watchlist item with current price."""

    ticker: str
    price: float
    change: float
    change_percent: float
    direction: str


class AddWatchlistRequest(BaseModel):
    """Request to add a ticker to watchlist."""

    ticker: str


def create_watchlist_router(
    conn: sqlite3.Connection,
    price_cache: PriceCache,
    market_source: MarketDataSource,
) -> APIRouter:
    """Create the watchlist router with dependencies."""
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("", response_model=list[WatchlistItem])
    async def get_current_watchlist() -> list[WatchlistItem]:
        """Get current watchlist with prices."""
        tickers = get_watchlist(conn, DEFAULT_USER_ID)
        items = []

        for ticker in tickers:
            price_update = price_cache.get(ticker)
            if price_update:
                items.append(
                    WatchlistItem(
                        ticker=ticker,
                        price=price_update.price,
                        change=price_update.change,
                        change_percent=price_update.change_percent,
                        direction=price_update.direction,
                    )
                )

        return items

    @router.post("", response_model=list[WatchlistItem])
    async def add_to_watchlist(request: AddWatchlistRequest) -> list[WatchlistItem]:
        """Add a ticker to the watchlist."""
        ticker = request.ticker.upper()

        # Check if already in watchlist
        existing = execute_query(
            conn,
            "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
            (DEFAULT_USER_ID, ticker),
        )
        if existing:
            logger.info("Ticker %s already in watchlist", ticker)
        else:
            # Add to watchlist
            watchlist_id = str(uuid4())
            execute_insert(
                conn,
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                (watchlist_id, DEFAULT_USER_ID, ticker, datetime.now(timezone.utc).isoformat()),
            )
            logger.info("Added %s to watchlist", ticker)

            # Add to market data source if not already tracking
            if ticker not in market_source.get_tickers():
                await market_source.add_ticker(ticker)
                logger.info("Started tracking %s in market data source", ticker)

        return await get_current_watchlist()

    @router.delete("/{ticker}", response_model=list[WatchlistItem])
    async def remove_from_watchlist(ticker: str) -> list[WatchlistItem]:
        """Remove a ticker from the watchlist."""
        ticker = ticker.upper()

        # Remove from watchlist
        execute_insert(
            conn,
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (DEFAULT_USER_ID, ticker),
        )
        logger.info("Removed %s from watchlist", ticker)

        # Check if ticker has any positions
        positions = execute_query(
            conn,
            "SELECT id FROM positions WHERE user_id = ? AND ticker = ?",
            (DEFAULT_USER_ID, ticker),
        )

        # If no positions, we can stop tracking it
        if not positions:
            if ticker in market_source.get_tickers():
                await market_source.remove_ticker(ticker)
                logger.info("Stopped tracking %s in market data source", ticker)

        return await get_current_watchlist()

    return router
