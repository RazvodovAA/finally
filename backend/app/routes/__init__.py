"""API routes for FinAlly backend."""

from .chat import create_chat_router
from .portfolio import create_portfolio_router
from .system import router as system_router
from .watchlist import create_watchlist_router

__all__ = [
    "create_chat_router",
    "create_portfolio_router",
    "create_watchlist_router",
    "system_router",
]
