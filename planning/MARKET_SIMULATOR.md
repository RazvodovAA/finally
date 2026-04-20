# Market Simulator

Approach and code structure for simulating realistic stock prices when no `MASSIVE_API_KEY` is configured.

## Overview

The simulator uses **Geometric Brownian Motion (GBM)** — the model underlying Black-Scholes option pricing. Prices evolve continuously with random noise, can never go negative (the exponential keeps them positive), and exhibit the lognormal distribution seen in real markets.

Two classes work together:
- `GBMSimulator` — pure math/state; call `step()` to advance all prices by one tick
- `SimulatorDataSource` — asyncio wrapper; calls `step()` every 500ms and writes to `PriceCache`

## GBM Math

At each time step, a stock price evolves as:

```
S(t+dt) = S(t) * exp((mu - sigma²/2) * dt + sigma * sqrt(dt) * Z)
```

| Symbol | Meaning |
|--------|---------|
| `S(t)` | Current price |
| `mu` | Annualized drift (expected return), e.g. 0.05 |
| `sigma` | Annualized volatility, e.g. 0.22 |
| `dt` | Time step as fraction of a trading year |
| `Z` | Correlated standard normal random variable |

**Time step calculation** — for 500ms updates over 252 trading days × 6.5 hours/day:
```python
TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR   # ~8.48e-8
```

This tiny `dt` produces sub-cent moves per tick that accumulate naturally over time.

## Correlated Moves

Real stocks don't move independently — tech stocks tend to move together. The simulator uses **Cholesky decomposition** of a sector-based correlation matrix to generate correlated random draws.

Given correlation matrix `C`, compute lower-triangular `L = cholesky(C)`. Then:
```
Z_correlated = L @ Z_independent
```
where `Z_independent` is a vector of independent standard normal draws.

### Correlation Structure

Defined in `seed_prices.py`:

```python
CORRELATION_GROUPS = {
    "tech":    {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}

INTRA_TECH_CORR    = 0.6   # Tech stocks move together
INTRA_FINANCE_CORR = 0.5   # Finance stocks move together
CROSS_GROUP_CORR   = 0.3   # Between sectors or unknown tickers
TSLA_CORR          = 0.3   # TSLA is in tech group but does its own thing
```

The Cholesky matrix is rebuilt whenever tickers are added or removed. It's O(n²) but n is always small (<50 tickers).

## Random Events

Each tick, every ticker has a 0.1% chance (`event_probability=0.001`) of a sudden 2-5% move:

```python
if random.random() < self._event_prob:
    shock_magnitude = random.uniform(0.02, 0.05)
    shock_sign = random.choice([-1, 1])
    self._prices[ticker] *= 1 + shock_magnitude * shock_sign
```

With 10 tickers at 2 ticks/sec: expect ~1 event every 50 seconds somewhere in the watchlist. Enough to keep the dashboard visually interesting.

## Seed Prices and Per-Ticker Parameters

Defined in `backend/app/market/seed_prices.py`:

```python
SEED_PRICES: dict[str, float] = {
    "AAPL": 190.00,
    "GOOGL": 175.00,
    "MSFT": 420.00,
    "AMZN": 185.00,
    "TSLA": 250.00,
    "NVDA": 800.00,
    "META": 500.00,
    "JPM": 195.00,
    "V": 280.00,
    "NFLX": 600.00,
}

TICKER_PARAMS: dict[str, dict[str, float]] = {
    "AAPL":  {"sigma": 0.22, "mu": 0.05},
    "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT":  {"sigma": 0.20, "mu": 0.05},
    "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA":  {"sigma": 0.50, "mu": 0.03},   # High volatility
    "NVDA":  {"sigma": 0.40, "mu": 0.08},   # High volatility, strong drift
    "META":  {"sigma": 0.30, "mu": 0.05},
    "JPM":   {"sigma": 0.18, "mu": 0.04},   # Low volatility (bank)
    "V":     {"sigma": 0.17, "mu": 0.04},   # Low volatility (payments)
    "NFLX":  {"sigma": 0.35, "mu": 0.05},
}

DEFAULT_PARAMS: dict[str, float] = {"sigma": 0.25, "mu": 0.05}
```

Tickers added dynamically (not in the seed list) start at `random.uniform(50.0, 300.0)` and use `DEFAULT_PARAMS`.

## GBMSimulator Implementation

```python
class GBMSimulator:
    DEFAULT_DT = 0.5 / (252 * 6.5 * 3600)  # ~8.48e-8

    def __init__(self, tickers: list[str], dt: float = DEFAULT_DT,
                 event_probability: float = 0.001) -> None: ...

    def step(self) -> dict[str, float]:
        """Advance all tickers one tick. Returns {ticker: new_price}. Hot path — called every 500ms."""
        n = len(self._tickers)
        z_independent = np.random.standard_normal(n)
        z_correlated = self._cholesky @ z_independent if self._cholesky is not None else z_independent

        result = {}
        for i, ticker in enumerate(self._tickers):
            mu, sigma = self._params[ticker]["mu"], self._params[ticker]["sigma"]
            drift     = (mu - 0.5 * sigma**2) * self._dt
            diffusion = sigma * math.sqrt(self._dt) * z_correlated[i]
            self._prices[ticker] *= math.exp(drift + diffusion)

            if random.random() < self._event_prob:
                self._prices[ticker] *= 1 + random.uniform(0.02, 0.05) * random.choice([-1, 1])

            result[ticker] = round(self._prices[ticker], 2)
        return result

    def add_ticker(self, ticker: str) -> None:
        """Add ticker; rebuilds Cholesky matrix."""

    def remove_ticker(self, ticker: str) -> None:
        """Remove ticker; rebuilds Cholesky matrix."""

    def get_price(self, ticker: str) -> float | None: ...

    def get_tickers(self) -> list[str]: ...
```

## SimulatorDataSource Implementation

```python
class SimulatorDataSource(MarketDataSource):
    def __init__(self, price_cache: PriceCache, update_interval: float = 0.5,
                 event_probability: float = 0.001) -> None: ...

    async def start(self, tickers: list[str]) -> None:
        self._sim = GBMSimulator(tickers=tickers, event_probability=self._event_prob)
        # Seed cache immediately so SSE has data before the first tick
        for ticker in tickers:
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def add_ticker(self, ticker: str) -> None:
        if self._sim:
            self._sim.add_ticker(ticker)
            # Seed cache immediately so new ticker has a price right away
            price = self._sim.get_price(ticker)
            if price is not None:
                self._cache.update(ticker=ticker, price=price)

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

## File Structure

```
backend/app/market/
├── seed_prices.py   # SEED_PRICES, TICKER_PARAMS, DEFAULT_PARAMS, CORRELATION_GROUPS, correlation constants
└── simulator.py     # GBMSimulator class + SimulatorDataSource
```

## Behavior Notes

- **Prices never go negative** — GBM is multiplicative (`exp()` is always positive)
- **Sub-cent moves per tick** — with `sigma=0.22` (AAPL) and `dt=8.48e-8`, a single tick move is ~$0.003 on a $190 stock; this accumulates naturally to realistic daily ranges
- **Realistic intraday ranges** — TSLA with `sigma=0.50` produces roughly ±1-2% intraday, similar to real TSLA behavior
- **Positive semi-definite correlation matrix** — Cholesky decomposition requires this; the sector-based structure (all correlations between 0 and 1, diagonal = 1) guarantees it
- **Event frequency** — 0.1% per tick per ticker; with 10 tickers at 2 ticks/sec, expect ~1 event every 50 seconds across the watchlist
- **Dynamic tickers** — when `add_ticker()` is called mid-session, Cholesky is rebuilt; O(n²) but n < 50, so negligible
