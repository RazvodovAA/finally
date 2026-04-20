# Market Data — Backend Design

Complete implementation blueprint for the market data layer: unified interface, GBM simulator, Massive API client, price cache, and SSE streaming.

---

## Module Layout

```
backend/app/market/
├── __init__.py        # Public exports
├── models.py          # PriceUpdate dataclass
├── interface.py       # MarketDataSource ABC
├── cache.py           # PriceCache (thread-safe)
├── factory.py         # create_market_data_source()
├── seed_prices.py     # Seed prices, GBM params, correlation config
├── simulator.py       # GBMSimulator + SimulatorDataSource
├── massive_client.py  # MassiveDataSource
└── stream.py          # SSE FastAPI router
```

---

## 1. `models.py` — Core Data Model

`PriceUpdate` is the only data structure that leaves the market data layer. Everything downstream (SSE, portfolio, trading) operates on this type.

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
    def change(self) -> float:
        return self.price - self.previous_price

    @property
    def change_percent(self) -> float:
        if self.previous_price == 0:
            return 0.0
        return (self.change / self.previous_price) * 100

    @property
    def direction(self) -> str:
        if self.price > self.previous_price:
            return "up"
        if self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "change": round(self.change, 4),
            "change_percent": round(self.change_percent, 4),
            "direction": self.direction,
            "timestamp": self.timestamp,
        }
```

On first update for a ticker, `previous_price == price` and `direction == "flat"`.

---

## 2. `cache.py` — Thread-Safe Price Cache

One writer (the data source background task), many readers (SSE stream, portfolio endpoints, trade execution). Uses a `threading.Lock` — safe for asyncio + thread-pool combinations.

```python
import threading
import time
from .models import PriceUpdate


class PriceCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._prices: dict[str, PriceUpdate] = {}
        self._version = 0

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        ts = timestamp if timestamp is not None else time.time()
        with self._lock:
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev is not None else price
            update = PriceUpdate(
                ticker=ticker,
                price=price,
                previous_price=previous_price,
                timestamp=ts,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        with self._lock:
            return self._prices.get(ticker)

    def get_price(self, ticker: str) -> float | None:
        update = self.get(ticker)
        return update.price if update is not None else None

    def get_all(self) -> dict[str, PriceUpdate]:
        with self._lock:
            return dict(self._prices)

    def remove(self, ticker: str) -> None:
        with self._lock:
            self._prices.pop(ticker, None)

    @property
    def version(self) -> int:
        with self._lock:
            return self._version
```

`version` is a monotonic counter that SSE uses for change detection — it only yields an event when the version has advanced since the last push.

---

## 3. `interface.py` — Abstract Base Class

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
        """Add ticker to the active set. No-op if already present."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Remove ticker from active set and from PriceCache."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Return the current list of actively tracked tickers."""
```

Both `SimulatorDataSource` and `MassiveDataSource` implement this ABC. All downstream code is source-agnostic.

---

## 4. `seed_prices.py` — Seed Prices and GBM Parameters

```python
SEED_PRICES: dict[str, float] = {
    "AAPL":  190.00,
    "GOOGL": 175.00,
    "MSFT":  420.00,
    "AMZN":  185.00,
    "TSLA":  250.00,
    "NVDA":  800.00,
    "META":  500.00,
    "JPM":   195.00,
    "V":     280.00,
    "NFLX":  600.00,
}

TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},  # high volatility, lower drift
    "NVDA":  {"sigma": 0.40, "mu": 0.08},  # high volatility, strong drift
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},
    "V":     {"sigma": 0.17, "mu": 0.04},
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}

# Sector groupings used to build correlation matrix
CORRELATION_GROUPS: dict[str, set[str]] = {
    "tech":    {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

INTRA_TECH_CORR    = 0.6   # tech stocks move together
INTRA_FINANCE_CORR = 0.5
CROSS_GROUP_CORR   = 0.3   # between sectors or unknown tickers
TSLA_CORR          = 0.3   # TSLA is in tech but does its own thing
```

Tickers added dynamically (not in the seed list) start at `random.uniform(50.0, 300.0)` and use `DEFAULT_PARAMS`.

---

## 5. `simulator.py` — GBM Simulator

### GBM Math

At each time step:

```
S(t+dt) = S(t) * exp((mu - sigma²/2) * dt + sigma * sqrt(dt) * Z)
```

Time step for 500ms updates scaled to a trading year (252 days × 6.5 hours):

```python
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR   # ~8.48e-8
```

### Correlated Moves via Cholesky Decomposition

```python
import numpy as np

def _build_cholesky(tickers: list[str]) -> np.ndarray | None:
    """Build lower-triangular Cholesky factor from sector-based correlation matrix."""
    n = len(tickers)
    if n == 0:
        return None
    C = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            corr = _pairwise_corr(tickers[i], tickers[j])
            C[i, j] = corr
            C[j, i] = corr
    return np.linalg.cholesky(C)


def _pairwise_corr(a: str, b: str) -> float:
    from .seed_prices import CORRELATION_GROUPS, INTRA_TECH_CORR, INTRA_FINANCE_CORR, CROSS_GROUP_CORR, TSLA_CORR
    if a == "TSLA" or b == "TSLA":
        return TSLA_CORR
    for group_tickers in CORRELATION_GROUPS.values():
        if a in group_tickers and b in group_tickers:
            if "AAPL" in group_tickers:   # tech group
                return INTRA_TECH_CORR
            return INTRA_FINANCE_CORR
    return CROSS_GROUP_CORR
```

The Cholesky matrix is rebuilt whenever tickers are added or removed. It is O(n²) but n is always small (< 50), so negligible cost.

### GBMSimulator Class

```python
import math
import random
import numpy as np
from .seed_prices import SEED_PRICES, TICKER_PARAMS, DEFAULT_PARAMS


class GBMSimulator:
    DEFAULT_DT = 0.5 / (252 * 6.5 * 3600)  # ~8.48e-8

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None
        for ticker in tickers:
            self._init_ticker(ticker)
        self._rebuild_cholesky()

    def _init_ticker(self, ticker: str) -> None:
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker, random.uniform(50.0, 300.0))
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        self._cholesky = _build_cholesky(self._tickers)

    def step(self) -> dict[str, float]:
        """Advance all tickers one tick. Returns {ticker: new_price}. Called every 500ms."""
        n = len(self._tickers)
        if n == 0:
            return {}
        z_independent = np.random.standard_normal(n)
        z_correlated = self._cholesky @ z_independent if self._cholesky is not None else z_independent

        result = {}
        for i, ticker in enumerate(self._tickers):
            mu = self._params[ticker]["mu"]
            sigma = self._params[ticker]["sigma"]
            drift     = (mu - 0.5 * sigma ** 2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            # Random shock: 0.1% chance per tick of a 2-5% sudden move
            if random.random() < self._event_prob:
                shock = random.uniform(0.02, 0.05) * random.choice([-1, 1])
                self._prices[ticker] *= (1 + shock)

            result[ticker] = round(self._prices[ticker], 2)
        return result

    def add_ticker(self, ticker: str) -> None:
        if ticker not in self._prices:
            self._init_ticker(ticker)
            self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        if ticker in self._prices:
            self._tickers.remove(ticker)
            del self._prices[ticker]
            del self._params[ticker]
            self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)
```

### SimulatorDataSource Class

```python
import asyncio
import logging
from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class SimulatorDataSource(MarketDataSource):
    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(tickers=tickers, event_probability=self._event_prob)
        # Seed cache immediately so SSE has data before the first tick
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)

    async def remove_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self) -> None:
        while True:
            try:
                if self._sim:
                    for ticker, price in self._sim.step().items():
                        self._cache.update(ticker=ticker, price=price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

**Behavior notes**:
- Prices never go negative — GBM is multiplicative (`exp()` always positive)
- Sub-cent moves per tick: with `sigma=0.22` and `dt=8.48e-8`, a single tick moves AAPL by ~$0.003
- Random events: 0.1% per tick per ticker; with 10 tickers at 2 ticks/sec, expect ~1 event every 50 seconds

---

## 6. `massive_client.py` — Massive API Data Source

Polls `GET /v2/snapshot/locale/us/markets/stocks/tickers` (all watched tickers in one call) every `poll_interval` seconds. The synchronous Massive REST client runs via `asyncio.to_thread()` to avoid blocking the event loop.

```python
import asyncio
import logging
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,  # 15s = safe for free tier (5 req/min)
    ) -> None:
        self._client = RESTClient(api_key=api_key)
        self._cache = price_cache
        self._poll_interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        self._tickers = list(tickers)
        # First poll immediately so cache is populated before clients connect
        await self._poll_once()
        self._task = asyncio.create_task(self._run_loop(), name="massive-poll-loop")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def add_ticker(self, ticker: str) -> None:
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            # New ticker will appear on the next poll cycle

    async def remove_ticker(self, ticker: str) -> None:
        if ticker in self._tickers:
            self._tickers.remove(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_once(self) -> None:
        if not self._tickers:
            return
        try:
            snapshots = await asyncio.to_thread(
                self._client.get_snapshot_all,
                market_type=SnapshotMarketType.STOCKS,
                tickers=self._tickers,
            )
            for snap in snapshots:
                if snap.last_trade is None:
                    continue
                self._cache.update(
                    ticker=snap.ticker,
                    price=snap.last_trade.price,
                    timestamp=snap.last_trade.timestamp / 1000.0,  # ms → seconds
                )
        except Exception:
            logger.exception("Massive API poll failed — retrying next interval")

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self._poll_interval)
            await self._poll_once()
```

**Error handling**: all exceptions in the poll loop are caught and logged without re-raising. A transient network error or rate limit hit retries on the next interval and does not crash the app.

**Rate limit guidance**:
- Free tier (5 req/min): `poll_interval=15.0`
- Paid tier: `poll_interval=2.0` to `poll_interval=5.0`

---

## 7. `factory.py` — Source Selection

```python
import os
from .cache import PriceCache
from .interface import MarketDataSource


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        from .massive_client import MassiveDataSource
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    from .simulator import SimulatorDataSource
    return SimulatorDataSource(price_cache=price_cache)
```

---

## 8. `stream.py` — SSE FastAPI Router

The SSE endpoint uses version-based change detection: it tracks the last `cache.version` it saw and only yields an event when the version advances.

```python
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from .cache import PriceCache


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter()

    @router.get("/api/stream/prices")
    async def stream_prices():
        return StreamingResponse(
            _price_event_generator(price_cache),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # disable nginx buffering
            },
        )

    return router


async def _price_event_generator(cache: PriceCache):
    last_version = -1
    while True:
        current_version = cache.version
        if current_version != last_version:
            last_version = current_version
            payload = {
                ticker: update.to_dict()
                for ticker, update in cache.get_all().items()
            }
            yield f"data: {json.dumps(payload)}\n\n"
        await asyncio.sleep(0.1)  # poll cache at 10Hz; events fire only on changes
```

**SSE event shape** (one JSON object with all tickers per event):

```json
data: {
  "AAPL": {
    "ticker": "AAPL",
    "price": 191.50,
    "previous_price": 191.20,
    "change": 0.30,
    "change_percent": 0.157,
    "direction": "up",
    "timestamp": 1714000000.0
  },
  "GOOGL": { "..." }
}
```

The client uses the native `EventSource` API; reconnection is automatic.

---

## 9. `__init__.py` — Public Exports

```python
from .models import PriceUpdate
from .cache import PriceCache
from .interface import MarketDataSource
from .factory import create_market_data_source
from .stream import create_stream_router

__all__ = [
    "PriceUpdate",
    "PriceCache",
    "MarketDataSource",
    "create_market_data_source",
    "create_stream_router",
]
```

---

## 10. FastAPI App Lifecycle Integration

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.market import PriceCache, create_market_data_source, create_stream_router

DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
                   "NVDA", "META", "JPM", "V", "NFLX"]

price_cache = PriceCache()
market_source = create_market_data_source(price_cache)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await market_source.start(DEFAULT_TICKERS)
    yield
    await market_source.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(create_stream_router(price_cache))
```

Expose `market_source` and `price_cache` as module-level singletons so API route handlers can call `add_ticker` / `remove_ticker` and read prices without dependency injection boilerplate.

---

## 11. Watchlist → Market Data Coupling

When a user adds a ticker to the watchlist (via `POST /api/watchlist`):

```python
@router.post("/api/watchlist")
async def add_to_watchlist(body: AddTickerRequest):
    ticker = body.ticker.upper()
    db.add_to_watchlist(ticker)              # persist to SQLite
    await market_source.add_ticker(ticker)   # start tracking prices
    return {"ticker": ticker}
```

When a ticker is removed (`DELETE /api/watchlist/{ticker}`):

```python
@router.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    ticker = ticker.upper()
    db.remove_from_watchlist(ticker)         # remove from SQLite
    await market_source.remove_ticker(ticker) # stops SSE updates, clears cache
    return {"ticker": ticker}
```

**Position tickers not on watchlist**: if the AI buys a ticker that isn't on the watchlist, it gets auto-added to both the watchlist and the market source so it appears in the SSE stream. The trade execution handler calls `add_ticker` when this happens.

---

## 12. Reading Prices in Other Endpoints

All non-SSE code reads from the shared `PriceCache` directly:

```python
# Portfolio valuation
for position in positions:
    current_price = price_cache.get_price(position.ticker) or position.avg_cost
    unrealized_pnl = (current_price - position.avg_cost) * position.quantity

# Trade execution (current price for market order fill)
price = price_cache.get_price(ticker)
if price is None:
    raise HTTPException(status_code=400, detail=f"No price available for {ticker}")
```

The `GET /api/portfolio` endpoint depends on `price_cache` for live prices. This dependency is intentional — the cache is the single source of truth for current prices.

---

## 13. Day Change Tracking

The PLAN requires a "daily change %" in the watchlist. The simulator has no concept of a market open price, so "daily" means **change since the app started** (i.e., the seed price).

Implementation: store the session-open price per ticker in a separate dict alongside `price_cache`. On first update for a ticker, record `open_price = price`. Day change % = `(current - open) / open * 100`.

For the Massive API, `snap.day.change_percent` is the official market day change and should be used instead. Add an optional `day_change_percent` field to `PriceUpdate` (defaults to `None`); the SSE payload includes it when available.

---

## Dependencies

```toml
# backend/pyproject.toml additions
dependencies = [
    "numpy>=1.26",   # GBM math (Cholesky, random normals)
    "massive",       # Polygon.io REST client
]
```

Install: `uv add numpy massive`
