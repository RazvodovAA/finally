"""FinAlly FastAPI application."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import DEFAULT_USER_ID, init_db, get_watchlist
from app.market import PriceCache, create_market_data_source, create_stream_router
from app.routes import create_chat_router, create_portfolio_router, create_watchlist_router, system_router

logger = logging.getLogger(__name__)


def create_app(db_path: str = "/app/db/finally.db") -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Configured FastAPI app ready to run.
    """
    app = FastAPI(
        title="FinAlly",
        description="AI-powered trading workstation",
        version="0.1.0",
    )

    # Initialize database
    logger.info("Initializing database at %s", db_path)
    conn = init_db(db_path)
    app.state.db_connection = conn

    # Initialize price cache and market data source
    logger.info("Initializing market data system")
    price_cache = PriceCache()
    app.state.price_cache = price_cache

    market_source = create_market_data_source(price_cache)
    app.state.market_source = market_source

    # CORS middleware (allow same-origin, though typically not needed for SPA)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers (must be before static files mount)
    logger.info("Mounting API routers")
    app.include_router(system_router)
    app.include_router(create_portfolio_router(conn, price_cache))
    app.include_router(create_watchlist_router(conn, price_cache, market_source))
    app.include_router(create_chat_router(conn, price_cache))
    app.include_router(create_stream_router(price_cache))

    @app.on_event("startup")
    async def startup_event() -> None:
        """Initialize market data source on app startup."""
        logger.info("Starting up market data source")
        watchlist = get_watchlist(conn, DEFAULT_USER_ID)
        logger.info("Initial watchlist: %s", watchlist)
        await market_source.start(watchlist)
        logger.info("Market data source started")

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Gracefully shut down market data source."""
        logger.info("Shutting down market data source")
        await market_source.stop()
        logger.info("Market data source stopped")

        # Close database connection
        from app.db import close_db_connection
        close_db_connection()
        logger.info("Database connection closed")

    # Serve static frontend files (mount at end so API routes take precedence)
    frontend_export_path = Path("/app/frontend/out")
    if frontend_export_path.exists():
        logger.info("Mounting static frontend files from %s", frontend_export_path)
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_export_path), html=True),
            name="frontend",
        )
    else:
        logger.warning("Frontend static files not found at %s", frontend_export_path)

    return app


# Create the app instance for uvicorn
# Note: When running via uvicorn, this will be called automatically
# Tests should use create_app() with their own db_path to avoid initialization
try:
    app = create_app()
except (OSError, FileNotFoundError):
    # During testing or in read-only environments, defer app creation
    app = None
