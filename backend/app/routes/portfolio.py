"""Portfolio and trade endpoints."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import (
    DEFAULT_USER_ID,
    execute_insert,
    get_position,
    get_positions,
    get_user_profile,
)
from app.market import PriceCache

logger = logging.getLogger(__name__)


class TradeRequest(BaseModel):
    """Request to execute a trade."""

    ticker: str
    side: str  # "buy" or "sell"
    quantity: float


class PositionResponse(BaseModel):
    """A single position in the portfolio."""

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    pnl_percent: float


class PortfolioResponse(BaseModel):
    """Portfolio summary response."""

    positions: list[PositionResponse]
    cash_balance: float
    total_value: float
    total_unrealized_pnl: float


class HistoryItem(BaseModel):
    """Portfolio snapshot for history."""

    timestamp: str
    total_value: float


def create_portfolio_router(conn: sqlite3.Connection, price_cache: PriceCache) -> APIRouter:
    """Create the portfolio router with database and price cache dependencies."""
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("", response_model=PortfolioResponse)
    async def get_portfolio() -> PortfolioResponse:
        """Get current portfolio with positions and cash balance."""
        user = get_user_profile(conn, DEFAULT_USER_ID)
        if not user:
            raise HTTPException(status_code=500, detail="User profile not found")

        positions_data = get_positions(conn, DEFAULT_USER_ID)
        positions = []
        total_unrealized_pnl = 0.0

        for pos in positions_data:
            current_price = price_cache.get_price(pos["ticker"])
            if current_price is None:
                continue

            unrealized_pnl = (current_price - pos["avg_cost"]) * pos["quantity"]
            pnl_percent = 0.0
            if pos["avg_cost"] > 0:
                pnl_percent = (unrealized_pnl / (pos["avg_cost"] * pos["quantity"])) * 100

            positions.append(
                PositionResponse(
                    ticker=pos["ticker"],
                    quantity=pos["quantity"],
                    avg_cost=pos["avg_cost"],
                    current_price=current_price,
                    unrealized_pnl=round(unrealized_pnl, 2),
                    pnl_percent=round(pnl_percent, 2),
                )
            )
            total_unrealized_pnl += unrealized_pnl

        # Calculate total portfolio value
        positions_value = sum(p.quantity * p.current_price for p in positions)
        total_value = user["cash_balance"] + positions_value

        return PortfolioResponse(
            positions=positions,
            cash_balance=round(user["cash_balance"], 2),
            total_value=round(total_value, 2),
            total_unrealized_pnl=round(total_unrealized_pnl, 2),
        )

    @router.post("/trade", response_model=dict)
    async def execute_trade(trade: TradeRequest) -> dict:
        """Execute a buy or sell trade."""
        # Validate input
        if trade.side not in ("buy", "sell"):
            raise HTTPException(status_code=400, detail="side must be 'buy' or 'sell'")

        if trade.quantity <= 0:
            raise HTTPException(status_code=400, detail="quantity must be positive")

        # Get current price
        current_price = price_cache.get_price(trade.ticker)
        if current_price is None:
            raise HTTPException(status_code=404, detail=f"No price available for {trade.ticker}")

        user = get_user_profile(conn, DEFAULT_USER_ID)
        if not user:
            raise HTTPException(status_code=500, detail="User profile not found")

        if trade.side == "buy":
            # Check sufficient cash
            cost = trade.quantity * current_price
            if user["cash_balance"] < cost:
                raise HTTPException(
                    status_code=422,
                    detail=f"Insufficient cash. Required: ${cost:.2f}, Available: ${user['cash_balance']:.2f}",
                )

            # Update position or create if new
            existing = get_position(conn, trade.ticker, DEFAULT_USER_ID)
            if existing:
                # Update average cost and quantity
                total_quantity = existing["quantity"] + trade.quantity
                total_cost = (existing["avg_cost"] * existing["quantity"]) + cost
                new_avg_cost = total_cost / total_quantity
                execute_insert(
                    conn,
                    "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? WHERE id = ?",
                    (total_quantity, new_avg_cost, datetime.now(timezone.utc).isoformat(), existing["id"]),
                )
            else:
                # Create new position
                position_id = str(uuid4())
                execute_insert(
                    conn,
                    "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (position_id, DEFAULT_USER_ID, trade.ticker, trade.quantity, current_price, datetime.now(timezone.utc).isoformat()),
                )

            # Deduct cash
            new_cash = user["cash_balance"] - cost
            execute_insert(
                conn,
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (new_cash, DEFAULT_USER_ID),
            )

        else:  # sell
            existing = get_position(conn, trade.ticker, DEFAULT_USER_ID)
            if not existing:
                raise HTTPException(
                    status_code=422,
                    detail=f"No position in {trade.ticker} to sell",
                )

            if existing["quantity"] < trade.quantity:
                raise HTTPException(
                    status_code=422,
                    detail=f"Insufficient shares. Own: {existing['quantity']}, Selling: {trade.quantity}",
                )

            # Update or delete position
            proceeds = trade.quantity * current_price
            if existing["quantity"] == trade.quantity:
                # Delete position
                execute_insert(
                    conn,
                    "DELETE FROM positions WHERE id = ?",
                    (existing["id"],),
                )
            else:
                # Update quantity
                new_quantity = existing["quantity"] - trade.quantity
                execute_insert(
                    conn,
                    "UPDATE positions SET quantity = ?, updated_at = ? WHERE id = ?",
                    (new_quantity, datetime.now(timezone.utc).isoformat(), existing["id"]),
                )

            # Add cash
            new_cash = user["cash_balance"] + proceeds
            execute_insert(
                conn,
                "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                (new_cash, DEFAULT_USER_ID),
            )

        # Record trade
        trade_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_id, DEFAULT_USER_ID, trade.ticker, trade.side, trade.quantity, current_price, datetime.now(timezone.utc).isoformat()),
        )

        # Record portfolio snapshot
        portfolio = await get_portfolio()
        snapshot_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (snapshot_id, DEFAULT_USER_ID, portfolio.total_value, datetime.now(timezone.utc).isoformat()),
        )

        return {
            "status": "success",
            "message": f"{trade.side.capitalize()} order executed: {trade.quantity} {trade.ticker} @ ${current_price:.2f}",
            "updated_portfolio": portfolio.model_dump(),
        }

    @router.get("/history", response_model=list[HistoryItem])
    async def get_portfolio_history() -> list[HistoryItem]:
        """Get portfolio value history for P&L chart."""
        from app.db import get_portfolio_snapshots

        snapshots = get_portfolio_snapshots(conn, DEFAULT_USER_ID)
        return [
            HistoryItem(
                timestamp=snap["recorded_at"],
                total_value=snap["total_value"],
            )
            for snap in snapshots
        ]

    return router
