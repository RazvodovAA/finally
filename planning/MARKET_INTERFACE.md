# Market Data Interface

Unified Python API for market data in FinAlly. Two implementations (simulator and Massive API) behind one abstract interface. All downstream code — SSE streaming, portfolio valuation, trade execution — is source-agnostic.

## Module Location

```
backend/app/market/
├── __init__.py        # Public exports
├── models.py          # PriceUpdate dataclass
├── interface.py       # MarketDataSource ABC
├── cache.py           # PriceCache
├── factory.py         # create_market_data_source()
├── massive_client.py  # MassiveDataSource
├── simulator.py       # SimulatorDataSource + GBMSimulator
├── seed_prices.py     # Seed prices and GBM parameters
└── stream.py          # SSE FastAPI router factory
```

## Core Data Model

```python
from dataclasses import dataclass, field
import time

@dataclass(frozen=True, slots=True)
class PriceUpdate:
    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds

    @property
    def change(self) -> float: ...          # price - previous_price
    @property
    def change_percent(self) -> float: ...  # % change
    @property
    def direction(self) -> str: ...         # "up", "down", or "flat"

    def to_dict(self) -> dict: ...          # JSON-serializable dict
```

`PriceUpdate` is the only data structure that leaves the market data layer.

## Abstract Interface

```python
from abc import ABC, abstractmethod

class MarketDataSource(ABC):

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates. Starts background task. Call once."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop background task and release resources. Safe to call multiple times."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Add a ticker to the active set. No-op if already present."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove ticker from active set and from PriceCache."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

Both implementations push updates into a shared `PriceCache`. The interface does not return prices directly — downstream code reads from the cache.

## Price Cache

Thread-safe in-memory store. One writer (the data source background task); many readers (SSE, portfolio, trading).

```python
class PriceCache:
    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        """Record new price. Computes direction/change from previous value."""

    def get(self, ticker: str) -> PriceUpdate | None:
        """Latest price for a ticker, or None if unknown."""

    def get_price(self, ticker: str) -> float | None:
        """Convenience: just the float price, or None."""

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices (shallow copy)."""

    def remove(self, ticker: str) -> None:
        """Remove a ticker (e.g., when removed from watchlist)."""

    @property
    def version(self) -> int:
        """Monotonic counter; incremented on every update. Used by SSE for change detection."""
```

On first update for a ticker, `previous_price == price` and `direction == "flat"`.

## Factory Function

```python
import os

def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        from .massive_client import MassiveDataSource
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    else:
        from .simulator import SimulatorDataSource
        return SimulatorDataSource(price_cache=price_cache)
```

## Public Imports

```python
from app.market import (
    PriceCache,
    PriceUpdate,
    MarketDataSource,
    create_market_data_source,
    create_stream_router,
)
```

## Lifecycle

```python
# App startup
cache = PriceCache()
source = create_market_data_source(cache)
await source.start(["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
                    "NVDA", "META", "JPM", "V", "NFLX"])

# Read prices (from any thread or coroutine)
update = cache.get("AAPL")          # PriceUpdate | None
price  = cache.get_price("AAPL")    # float | None
all_prices = cache.get_all()        # dict[str, PriceUpdate]

# Dynamic watchlist changes
await source.add_ticker("PYPL")     # Simulator: seeds cache immediately
await source.remove_ticker("GOOGL") # Removes from cache and active set

# App shutdown
await source.stop()
```

## SSE Integration

```python
from app.market import create_stream_router

router = create_stream_router(price_cache)
# Mounts GET /api/stream/prices  →  text/event-stream
app.include_router(router)
```

The SSE endpoint uses version-based change detection: it tracks the last `cache.version` it sent and only yields an event when the version has advanced. Each event is a JSON payload of all current prices:

```json
{
  "AAPL": {"ticker": "AAPL", "price": 191.50, "previous_price": 191.20,
           "change": 0.30, "change_percent": 0.157, "direction": "up", "timestamp": 1714000000.0},
  "GOOGL": { "..." }
}
```

## Massive Implementation

`MassiveDataSource` polls `GET /v2/snapshot/locale/us/markets/stocks/tickers` (all watched tickers in one call) every `poll_interval` seconds (default 15s for free tier).

- First poll happens immediately in `start()` so the cache has data before clients connect
- The synchronous Massive REST client runs via `asyncio.to_thread()` to avoid blocking the event loop
- Poll failures are logged and swallowed; the loop retries on the next interval
- `add_ticker()` appends to the ticker list; the new ticker appears on the next poll cycle

## Simulator Implementation

`SimulatorDataSource` wraps `GBMSimulator` in an asyncio loop, calling `step()` every 500ms.

- Seeds the cache immediately in `start()` with initial prices so SSE has data right away
- `add_ticker()` also seeds the cache immediately (no wait for the next step)
- See `MARKET_SIMULATOR.md` for the GBM math and correlation structure

## Design Notes

- **Strategy pattern**: both implementations satisfy the same ABC; all downstream code is source-agnostic
- **PriceCache as single point of truth**: producers write, consumers read; no direct coupling between data source and SSE/portfolio code
- **Thread safety**: `PriceCache` uses a `threading.Lock`; safe for asyncio + thread-pool combinations
- **No day-change tracking**: `PriceCache` tracks price-to-price change (tick-to-tick), not open-to-current. The Massive API provides `day.change_percent` but it is not currently stored; add it to `PriceUpdate` if the watchlist needs official day % change.
