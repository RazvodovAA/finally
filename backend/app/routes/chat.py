"""Chat endpoint for AI trading assistant."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import DEFAULT_USER_ID, execute_insert, get_chat_messages
from app.llm import ChatResponse, call_llm

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Request to send a chat message."""

    message: str


class ChatResponseModel(BaseModel):
    """Response from chat endpoint."""

    message: str
    trades: list[dict] = []
    watchlist_changes: list[dict] = []


def _format_portfolio_context(portfolio_data: dict) -> str:
    """Format portfolio data as a readable context string for LLM.

    Args:
        portfolio_data: Portfolio response from /api/portfolio endpoint.

    Returns:
        Formatted context string.
    """
    lines = [
        f"Cash Balance: ${portfolio_data['cash_balance']:,.2f}",
        f"Total Portfolio Value: ${portfolio_data['total_value']:,.2f}",
        f"Total Unrealized P&L: ${portfolio_data['total_unrealized_pnl']:,.2f}",
        "",
        "POSITIONS:",
    ]

    if portfolio_data["positions"]:
        for pos in portfolio_data["positions"]:
            lines.append(
                f"  {pos['ticker']}: {pos['quantity']} shares @ ${pos['avg_cost']:.2f} "
                f"(current: ${pos['current_price']:.2f}, P&L: ${pos['unrealized_pnl']:.2f}, "
                f"{pos['pnl_percent']:+.2f}%)"
            )
    else:
        lines.append("  (None - fully in cash)")

    return "\n".join(lines)


def _format_conversation_history(messages: list[dict]) -> list[dict]:
    """Format database messages as LLM conversation history.

    Args:
        messages: Chat messages from database.

    Returns:
        List of {"role": "user"|"assistant", "content": "..."} dicts.
    """
    history = []
    for msg in messages:
        history.append({
            "role": msg["role"],
            "content": msg["content"],
        })
    return history


def create_chat_router(conn: sqlite3.Connection, price_cache=None) -> APIRouter:
    """Create the chat router with database dependency.

    Args:
        conn: SQLite connection.
        price_cache: Optional PriceCache instance for portfolio context.

    Returns:
        APIRouter with /api/chat endpoint.
    """
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    @router.post("", response_model=ChatResponseModel)
    async def send_message(request: ChatRequest) -> ChatResponseModel:
        """Send a chat message and get AI response with auto-executed trades.

        Args:
            request: Chat request with user message.

        Returns:
            Chat response with message, trades, and watchlist changes.

        Raises:
            HTTPException: If portfolio fetch fails or LLM call fails.
        """
        logger.info("Chat message from user: %s", request.message)

        try:
            # Build portfolio context directly
            from app.db import get_positions, get_user_profile

            user = get_user_profile(conn, DEFAULT_USER_ID)
            if not user:
                raise HTTPException(status_code=500, detail="User profile not found")

            positions_data = get_positions(conn, DEFAULT_USER_ID)
            positions = []
            total_unrealized_pnl = 0.0

            if price_cache:
                for pos in positions_data:
                    current_price = price_cache.get_price(pos["ticker"])
                    if current_price is None:
                        continue

                    unrealized_pnl = (current_price - pos["avg_cost"]) * pos["quantity"]
                    pnl_percent = 0.0
                    if pos["avg_cost"] > 0:
                        pnl_percent = (unrealized_pnl / (pos["avg_cost"] * pos["quantity"])) * 100

                    positions.append({
                        "ticker": pos["ticker"],
                        "quantity": pos["quantity"],
                        "avg_cost": pos["avg_cost"],
                        "current_price": current_price,
                        "unrealized_pnl": round(unrealized_pnl, 2),
                        "pnl_percent": round(pnl_percent, 2),
                    })
                    total_unrealized_pnl += unrealized_pnl

                # Calculate total portfolio value
                positions_value = sum(p["quantity"] * p["current_price"] for p in positions)
                total_value = user["cash_balance"] + positions_value
            else:
                total_value = user["cash_balance"]

            portfolio_dict = {
                "positions": positions,
                "cash_balance": round(user["cash_balance"], 2),
                "total_value": round(total_value, 2),
                "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            }
            portfolio_context = _format_portfolio_context(portfolio_dict)

            # Load recent conversation history (last 20 messages)
            history_records = get_chat_messages(conn, DEFAULT_USER_ID, limit=20)
            conversation_history = _format_conversation_history(history_records)

            # Call LLM
            llm_response: ChatResponse = await call_llm(
                user_message=request.message,
                portfolio_context=portfolio_context,
                conversation_history=conversation_history,
            )

        except Exception as e:
            logger.error("Failed to get LLM response: %s", e)
            raise HTTPException(status_code=500, detail=f"Chat service error: {e}") from e

        # Store user message in database
        user_msg_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO chat_messages (id, user_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                user_msg_id,
                DEFAULT_USER_ID,
                "user",
                request.message,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        # Execute trades and watchlist changes from LLM response
        executed_trades = []
        executed_changes = []
        trade_errors = []

        # Helper to execute a trade
        async def execute_trade_direct(
            ticker: str, side: str, quantity: float
        ) -> tuple[bool, str, dict | None]:
            """Execute a trade and return status."""
            from app.db import get_position, get_user_profile

            try:
                # Validate input
                if side not in ("buy", "sell"):
                    return False, f"Invalid side: {side}", None

                if quantity <= 0:
                    return False, "Quantity must be positive", None

                # Get current price
                if not price_cache:
                    return False, "Price cache not available", None

                current_price = price_cache.get_price(ticker)
                if current_price is None:
                    return False, f"No price available for {ticker}", None

                user = get_user_profile(conn, DEFAULT_USER_ID)
                if not user:
                    return False, "User profile not found", None

                if side == "buy":
                    # Check sufficient cash
                    cost = quantity * current_price
                    if user["cash_balance"] < cost:
                        return False, f"Insufficient cash. Need ${cost:.2f}, have ${user['cash_balance']:.2f}", None

                    # Update position or create if new
                    existing = get_position(conn, ticker, DEFAULT_USER_ID)
                    if existing:
                        total_quantity = existing["quantity"] + quantity
                        total_cost = (existing["avg_cost"] * existing["quantity"]) + cost
                        new_avg_cost = total_cost / total_quantity
                        execute_insert(
                            conn,
                            "UPDATE positions SET quantity = ?, avg_cost = ?, updated_at = ? WHERE id = ?",
                            (total_quantity, new_avg_cost, datetime.now(timezone.utc).isoformat(), existing["id"]),
                        )
                    else:
                        position_id = str(uuid4())
                        execute_insert(
                            conn,
                            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (position_id, DEFAULT_USER_ID, ticker, quantity, current_price, datetime.now(timezone.utc).isoformat()),
                        )

                    # Deduct cash
                    new_cash = user["cash_balance"] - cost
                    execute_insert(
                        conn,
                        "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
                        (new_cash, DEFAULT_USER_ID),
                    )

                else:  # sell
                    existing = get_position(conn, ticker, DEFAULT_USER_ID)
                    if not existing:
                        return False, f"No position in {ticker} to sell", None

                    if existing["quantity"] < quantity:
                        return False, f"Insufficient shares. Own {existing['quantity']}, selling {quantity}", None

                    # Update or delete position
                    proceeds = quantity * current_price
                    if existing["quantity"] == quantity:
                        execute_insert(
                            conn,
                            "DELETE FROM positions WHERE id = ?",
                            (existing["id"],),
                        )
                    else:
                        new_quantity = existing["quantity"] - quantity
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
                    (trade_id, DEFAULT_USER_ID, ticker, side, quantity, current_price, datetime.now(timezone.utc).isoformat()),
                )

                msg = f"{side.capitalize()} {quantity} {ticker} @ ${current_price:.2f}"
                return True, msg, None

            except Exception as e:
                return False, str(e), None

        if llm_response.trades:
            logger.info("Executing %d trades from LLM", len(llm_response.trades))
            for trade in llm_response.trades:
                success, msg, _ = await execute_trade_direct(
                    trade.ticker.upper(),
                    trade.side.lower(),
                    trade.quantity,
                )
                executed_trades.append({
                    "ticker": trade.ticker.upper(),
                    "side": trade.side.lower(),
                    "quantity": trade.quantity,
                    "status": "executed" if success else "failed",
                    "message": msg if success else None,
                    "error": msg if not success else None,
                })
                if not success:
                    trade_errors.append(msg)
                else:
                    logger.info("Trade executed: %s", msg)

        if llm_response.watchlist_changes:
            logger.info("Executing %d watchlist changes from LLM", len(llm_response.watchlist_changes))
            for change in llm_response.watchlist_changes:
                try:
                    from app.db import execute_query

                    ticker = change.ticker.upper()
                    action = change.action.lower()

                    if action == "add":
                        # Check if already in watchlist
                        existing = execute_query(
                            conn,
                            "SELECT id FROM watchlist WHERE user_id = ? AND ticker = ?",
                            (DEFAULT_USER_ID, ticker),
                        )
                        if not existing:
                            watchlist_id = str(uuid4())
                            execute_insert(
                                conn,
                                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                                (watchlist_id, DEFAULT_USER_ID, ticker, datetime.now(timezone.utc).isoformat()),
                            )
                            logger.info("Added %s to watchlist", ticker)
                        executed_changes.append({
                            "ticker": ticker,
                            "action": "add",
                            "status": "executed",
                        })

                    elif action == "remove":
                        # Remove from watchlist
                        execute_insert(
                            conn,
                            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
                            (DEFAULT_USER_ID, ticker),
                        )
                        logger.info("Removed %s from watchlist", ticker)
                        executed_changes.append({
                            "ticker": ticker,
                            "action": "remove",
                            "status": "executed",
                        })

                except Exception as e:
                    error_msg = str(e)
                    executed_changes.append({
                        "ticker": change.ticker.upper(),
                        "action": change.action.lower(),
                        "status": "failed",
                        "error": error_msg,
                    })
                    logger.warning("Watchlist change failed: %s", error_msg)

        # Build final message to user (append errors if any)
        final_message = llm_response.message
        if trade_errors:
            final_message += f"\n\nNote: Some trades failed: {'; '.join(trade_errors)}"

        # Store assistant message in database with executed actions
        actions_json = json.dumps({
            "trades": executed_trades,
            "watchlist_changes": executed_changes,
        })
        assistant_msg_id = str(uuid4())
        execute_insert(
            conn,
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                assistant_msg_id,
                DEFAULT_USER_ID,
                "assistant",
                final_message,
                actions_json,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        return ChatResponseModel(
            message=final_message,
            trades=executed_trades,
            watchlist_changes=executed_changes,
        )

    return router
