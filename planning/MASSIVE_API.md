# Massive API Reference (formerly Polygon.io)

Reference documentation for the Massive REST API as used in FinAlly.

## Overview

- **Base URL**: `https://api.massive.com` (legacy `https://api.polygon.io` still redirects)
- **Python package**: `massive` (`uv add massive`)
- **Min Python**: 3.9+
- **Auth**: API key via `MASSIVE_API_KEY` env var or `RESTClient(api_key=...)`
- **Auth header**: `Authorization: Bearer <API_KEY>` (handled automatically by the client)

## Rate Limits

| Tier | Limit |
|------|-------|
| Free | 5 requests/minute |
| Paid | Unlimited (stay under 100 req/s) |

For FinAlly: free tier → poll every 15s; paid → every 2-5s.

## Client Initialization

```python
from massive import RESTClient

# Reads MASSIVE_API_KEY from environment automatically
client = RESTClient()

# Or pass explicitly
client = RESTClient(api_key="your_key_here")

# Enable request/response tracing for debugging
client = RESTClient(api_key="your_key_here", trace=True)
```

## Endpoints Used in FinAlly

### 1. Snapshot — Multiple Tickers (Primary Endpoint)

Gets current prices for multiple tickers in a single API call. This is the main polling endpoint.

**REST**: `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,GOOGL,MSFT`

**Python client** (v2 — used in current implementation):
```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient()

snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
)

for snap in snapshots:
    price = snap.last_trade.price
    timestamp_ms = snap.last_trade.timestamp  # Unix milliseconds
    day_change_pct = snap.day.change_percent
```

**Response structure per ticker**:
```json
{
  "ticker": "AAPL",
  "last_trade": {
    "price": 191.50,
    "size": 100,
    "exchange": "XNAS",
    "timestamp": 1714000000000
  },
  "last_quote": {
    "bid_price": 191.49,
    "ask_price": 191.51,
    "bid_size": 500,
    "ask_size": 300,
    "timestamp": 1714000000100
  },
  "day": {
    "open": 189.00,
    "high": 193.00,
    "low": 188.50,
    "close": 191.50,
    "volume": 52000000,
    "previous_close": 188.00,
    "change": 3.50,
    "change_percent": 1.86
  }
}
```

**Fields extracted by FinAlly**:
- `last_trade.price` — current price for display and trade execution
- `last_trade.timestamp` — Unix milliseconds; divide by 1000 for seconds
- `day.previous_close` — for day change calculation (not currently used in cache; reserved for future use)
- `day.change_percent` — day % change (not currently used; available for watchlist display)

> **Note**: `get_snapshot_all()` is a v2 endpoint. The v3 alternative is `list_universal_snapshots(ticker_any_of=[...])`, which returns an iterator of `UniversalSnapshot` objects and supports additional asset types (options, forex, crypto). The v2 endpoint is still functional and is what the current implementation uses.

### 2. Single Ticker Snapshot

```python
snapshot = client.get_snapshot_ticker(
    market_type=SnapshotMarketType.STOCKS,
    ticker="AAPL",
)
price = snapshot.last_trade.price
bid = snapshot.last_quote.bid_price
ask = snapshot.last_quote.ask_price
day_range = (snapshot.day.low, snapshot.day.high)
```

### 3. Previous Close

```python
for agg in client.get_previous_close_agg(ticker="AAPL"):
    print(f"Previous close: {agg.close}")
    print(f"OHLC: O={agg.open} H={agg.high} L={agg.low} C={agg.close}")
    print(f"Volume: {agg.volume}")
```

### 4. Historical Aggregates (OHLCV Bars)

```python
aggs = list(client.list_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="day",      # "minute", "hour", "day", "week", "month"
    from_="2024-01-01",
    to="2024-01-31",
    limit=50000,         # Controls page size; client auto-paginates
))

for a in aggs:
    print(f"t={a.timestamp} O={a.open} H={a.high} L={a.low} C={a.close} V={a.volume}")
```

### 5. Last Trade / Last Quote

```python
trade = client.get_last_trade(ticker="AAPL")
print(f"Price: {trade.price}, Size: {trade.size}")

quote = client.get_last_quote(ticker="AAPL")
print(f"Bid: {quote.bid} x {quote.bid_size}")
print(f"Ask: {quote.ask} x {quote.ask_size}")
```

## How FinAlly Uses the API

The `MassiveDataSource` runs as a background asyncio task:

1. Collects all tickers from the active watchlist
2. Calls `get_snapshot_all()` with those tickers (one API call, runs in thread pool)
3. Extracts `last_trade.price` and `last_trade.timestamp` from each snapshot
4. Writes to the shared in-memory `PriceCache`
5. Sleeps for `poll_interval` seconds (default 15s), then repeats

```python
async def _poll_once(self) -> None:
    snapshots = await asyncio.to_thread(
        self._client.get_snapshot_all,
        market_type=SnapshotMarketType.STOCKS,
        tickers=self._tickers,
    )
    for snap in snapshots:
        self._cache.update(
            ticker=snap.ticker,
            price=snap.last_trade.price,
            timestamp=snap.last_trade.timestamp / 1000.0,  # ms → seconds
        )
```

The synchronous Massive client is run via `asyncio.to_thread()` to avoid blocking the event loop.

## Error Handling

The Massive client raises exceptions for HTTP errors:
- **401**: Invalid API key
- **403**: Endpoint not available on your plan
- **429**: Rate limit exceeded (free tier: 5 req/min)
- **5xx**: Server error (client has built-in retry)

`MassiveDataSource` catches all exceptions in the poll loop and logs them without re-raising, so a transient network error or rate limit hit doesn't crash the app — it retries on the next interval.

## Notes

- The snapshot endpoint returns all requested tickers in one call — critical for staying within free-tier rate limits
- Timestamps from the API are Unix milliseconds; divide by 1000 for seconds
- During market-closed hours, `last_trade.price` is the last traded price (may include after-hours)
- The `day` object resets at market open; pre-market values may reflect the previous session
- `list_aggs()` auto-paginates by default; `limit` controls page size, not total results
