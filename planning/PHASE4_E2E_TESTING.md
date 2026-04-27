# Phase 4: E2E Testing & Bug Triage

**Status**: Infrastructure setup complete. Smoke tests created. Awaiting Phase 3 frontend completion for full test suite.

**Timeline**: Phase 4 runs parallel with Phase 3. Infrastructure is ready now; full tests will run after Phase 3 is functional.

---

## E2E Testing Infrastructure

### Playwright Setup

- **Framework**: Playwright (v1.50.0) for cross-browser E2E testing
- **Config**: `test/playwright.config.ts` with Chrome/Chromium focus
- **Structure**: Tests organized in `test/specs/` by feature area

### Test Docker Compose (`test/docker-compose.test.yml`)

Two-service setup:

1. **API Service**
   - Builds and runs the full FinAlly container (Dockerfile multi-stage)
   - Runs with fresh SQLite volume (`finally-test-data`)
   - Sets `LLM_MOCK=true` for deterministic responses
   - Exposes port 8000
   - Includes healthcheck: `GET /api/health` polling (10 retries, 3s interval)

2. **Playwright Service**
   - Runs Playwright test runner in `mcr.microsoft.com/playwright:v1.50.0-noble` container
   - Depends on `api` service with `service_healthy` condition
   - Mounts `test/` directory for test specs
   - Runs `npm install && npx playwright test`

### Test Execution Flow

```
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit
  ↓
Build Dockerfile (Node stage + Python stage)
  ↓
Start API container with healthcheck loop
  ↓
API becomes healthy (responds to /api/health)
  ↓
Start Playwright container (depends_on: healthy)
  ↓
npm install (Playwright deps)
  ↓
npx playwright test (runs all specs in test/specs/*.spec.ts)
  ↓
Exit with test results (JUnit XML, HTML report, traces)
```

---

## Test Specifications

### Smoke Tests (`test/specs/smoke.spec.ts`)

**Status**: ✓ Created (framework ready, waits for frontend completion)

Tests:
1. **Page Loads with Title** — Verifies `/` loads and contains "FinAlly"
2. **API Health Check** — `GET /api/health` returns 200 with status field
3. **Watchlist Endpoint** — `GET /api/watchlist` returns default 10 tickers (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)
4. **Portfolio Endpoint** — `GET /api/portfolio` returns cash_balance=10000, positions, total_value, unrealized_pnl
5. **SSE Stream Available** — `GET /api/stream/prices` with `Accept: text/event-stream` returns 200/206

**Blockers**: None. Tests can run immediately against the API even while frontend is being built.

### Watchlist Tests (`test/specs/watchlist.spec.ts`)

**Status**: 📋 Template needed (pending Phase 3 frontend)

Tests:
- Add ticker via UI (e.g., PYPL, ADBE, NFLX)
- Verify ticker appears in watchlist with live price
- Verify simulator/market data starts tracking new ticker
- Remove ticker from watchlist
- Verify ticker disappears from grid
- Handle duplicate ticker (should not add twice or show error)
- Handle invalid ticker (non-existent symbol)
- Verify price stream includes new ticker prices

**Dependencies**:
- Frontend watchlist component with add/remove UI
- Watchlist API working (`POST /api/watchlist`, `DELETE /api/watchlist/{ticker}`)
- Price stream updating for new tickers

### Trading Tests (`test/specs/trading.spec.ts`)

**Status**: 📋 Template needed (pending Phase 3 frontend + chat API)

Tests:

**Happy Path**:
- Buy order: Enter ticker, quantity, click Buy
  - Cash decreases by (quantity × price)
  - Position appears in positions table
  - Portfolio total value updates
  - Portfolio heatmap includes new position
- Sell order: Enter ticker, quantity, click Sell
  - Cash increases by (quantity × price)
  - Position updates (quantity decreases) or deletes (if quantity goes to 0)
  - Portfolio total value updates

**Edge Cases**:
- Buy with exactly cash balance (e.g., buy 10 shares at $1000 = $10k cash)
- Sell all shares (position should disappear)
- Very large trade quantity
- Buy then immediately sell same ticker

**Error Cases**:
- Buy without sufficient cash → error shown, no trade executes
- Sell more shares than owned → error shown, no trade executes
- Invalid ticker in form → error shown
- Empty quantity field → error shown

**Dependencies**:
- Frontend trade form UI (ticker, quantity, buy/sell buttons)
- `POST /api/portfolio/trade` endpoint fully functional
- Error response handling in frontend

### Portfolio Tests (`test/specs/portfolio.spec.ts`)

**Status**: 📋 Template needed (pending Phase 3 frontend visualization)

Tests:

**Heatmap (Treemap)**:
- Renders with correct number of rectangles (one per position)
- Rectangle sizes proportional to portfolio weight
- Colors correct (green for positive P&L, red for negative, gray for neutral)
- Clicking rectangle shows position details
- Empty state shows placeholder when no positions

**P&L Chart**:
- Renders with title and axes
- X-axis: time, Y-axis: portfolio value
- Has data points after trades execute
- Updated in near-real-time as prices change
- Empty state (no data yet) shows placeholder

**Positions Table**:
- Columns: Ticker, Quantity, Avg Cost, Current Price, Unrealized P&L ($), % Change
- All rows visible and scrollable
- Data updates on price changes
- Clicking row shows detail view

**Header Stats**:
- Total portfolio value (live, updates with prices)
- Cash balance (updates on trades)
- Connection status indicator (green/yellow/red)

**Dependencies**:
- Frontend visualization components (Recharts or Lightweight Charts)
- Portfolio data API (`GET /api/portfolio`, `GET /api/portfolio/history`)
- Real-time price updates flowing to frontend

### Chat Tests (`test/specs/chat.spec.ts`)

**Status**: 📋 Template needed (pending Phase 3 chat UI + chat API)

Tests:

**Basic**:
- Send message to chat panel
- Verify message appears in chat history
- Verify LLM response received and displayed
- Loading indicator shows while waiting for response

**Auto-Execution**:
- LLM suggests buy trade → verify trade executes
- LLM suggests sell trade → verify trade executes
- LLM suggests adding ticker → verify watchlist updates
- LLM suggests removing ticker → verify watchlist updates

**Error Handling**:
- LLM trade fails validation (insufficient cash) → error shown in chat
- LLM response with malformed JSON → error message shown
- Chat message empty → form validates and prevents send

**Mock Mode**:
- With `LLM_MOCK=true`, responses are deterministic (e.g., always buy AAPL for 10 shares)
- Useful for fast, repeatable tests without OpenAI API calls

**Dependencies**:
- Frontend chat UI (input, history, loading state)
- `POST /api/chat` endpoint with structured output parsing
- LLM integration (LiteLLM → OpenAI/mock)
- Trade auto-execution logic

### SSE Tests (`test/specs/sse.spec.ts`)

**Status**: 📋 Template needed (pending Phase 3 SSE integration)

Tests:

**Streaming**:
- Prices update via SSE connection
- Multiple price updates in sequence
- All watched tickers receive updates
- Updates include: ticker, price, previous_price, timestamp, direction

**UI Animations**:
- Price flash effect: background color changes (green/red) on price change
- Fade-out animation: color fades back to normal over ~500ms
- Timing: update visible within 100ms of SSE event

**Change % Display**:
- Daily change % displayed for each ticker
- Updates as prices change
- Correctly formatted (e.g., "+2.5%" or "-1.2%")

**Sparklines**:
- Mini-chart accumulates price data since page load
- Updates on each new price
- Shows trend (up/down/flat)
- No data loss on reconnect

**Connection Resilience**:
- Connection status indicator starts green (connected)
- Kill backend container → indicator goes yellow (reconnecting)
- Restart backend → indicator returns green, no data loss
- Data resumes flowing after reconnect

**Dependencies**:
- Frontend SSE EventSource connection to `/api/stream/prices`
- Frontend UI components for price display, sparklines, animations
- Connection status indicator component
- Market data simulator/API continuously generating prices

### Error Tests (`test/specs/error.spec.ts`)

**Status**: 📋 Template needed (pending all features)

Tests:

**Form Validation**:
- Empty ticker field → error shown
- Empty quantity field → error shown
- Non-numeric quantity → error shown
- Negative quantity → error shown

**Trade Validation**:
- Insufficient cash for buy → specific error message
- Insufficient shares for sell → specific error message
- Ticker doesn't exist → specific error message

**Watchlist Validation**:
- Add duplicate ticker → error shown or silently ignored
- Add non-existent ticker → allow (simulator will track) or error
- Remove non-existent ticker → error shown

**Chat Validation**:
- Send empty message → prevented by form validation
- Send very long message → truncate or error
- LLM response timeout → error shown, user can retry

**Edge Cases**:
- Rapid successive trades (buy-sell-buy in quick succession)
- Trading the last share (position should delete, not leave 0 shares)
- Price change during trade (show current price before confirming)
- Network disconnect during trade (optimistic update or rollback)

**Dependencies**:
- Robust error handling in frontend and API
- Validation on both sides
- User-friendly error messages

---

## Test Execution Strategy

### Local Development

```bash
cd test
npm install
npm run test          # Run all tests headless
npm run test:headed   # See browser
npm run test:debug    # Interactive debugger
npm run test:ui       # Playwright Inspector dashboard
```

### Docker (CI/CD)

```bash
docker compose -f test/docker-compose.test.yml up --build --abort-on-container-exit
# Automatically:
# 1. Builds Docker image
# 2. Starts API container
# 3. Waits for health check
# 4. Runs Playwright tests
# 5. Exits with test status code
```

### GitHub Actions (Future)

Tests can be integrated into CI with:
- Event: push to `main`, PR to `main`, scheduled daily
- Runs: `docker compose -f test/docker-compose.test.yml up`
- Artifacts: JUnit XML report, HTML report, failure traces
- Blocking: PR checks pass if all tests pass

---

## Bug Triage Process

### When a Bug is Found

1. **Identify Root Cause**
   - Reproduce consistently
   - Isolate: is it frontend, backend API, or SSE?
   - Prove the problem with evidence (logs, network trace, test failure)

2. **File Bug Report**
   - Create entry in `planning/BUGS.md` (new file for Phase 4)
   - Format:
     ```
     ## [Severity] Title
     
     **Description**: What is broken
     **Steps to Reproduce**: 1. ... 2. ... 3. ...
     **Expected Behavior**: What should happen
     **Actual Behavior**: What actually happens
     **Screenshots/Logs**: Evidence
     **Affected Component**: Frontend / Backend API / Market Data / Chat
     **Assigned To**: @[agent-name]
     **Status**: Open / In Progress / Fixed / Blocked
     ```

3. **Tag Responsible Agent**
   - Frontend bugs → Frontend Engineer
   - API bugs → Backend Engineer
   - Market data bugs → Market Data Engineer
   - Chat bugs → Backend Engineer (LLM integration owner)

4. **Verify Fix**
   - Ensure test added to prevent regression
   - Re-run test suite to confirm fix
   - Move bug to "Fixed" status

### Severity Levels

- **P0 (Critical)**: Blocking full feature (e.g., API won't start, app crashes on load)
- **P1 (High)**: Major feature broken (e.g., trades don't execute, prices don't stream)
- **P2 (Medium)**: Feature incomplete (e.g., error message missing, UI not pretty)
- **P3 (Low)**: Minor issue (e.g., button spacing, log verbosity)

---

## Phase 4 Timeline

| Phase | Milestone | Status | Notes |
|-------|-----------|--------|-------|
| 4a | Test infrastructure | ✓ DONE | Docker setup, Playwright config, CI/CD ready |
| 4b | Smoke tests | ✓ DONE | API health, endpoints, basic connectivity |
| 4c | Phase 3 completion | IN PROGRESS | Frontend + Chat API |
| 4d | Feature tests | PENDING | Watchlist, Trading, Portfolio, Chat, SSE |
| 4e | Error tests | PENDING | Validation, edge cases, resilience |
| 4f | Bug triage & fixes | PENDING | Identify and track issues from testing |
| 4g | Performance tuning | PENDING | Optimize load time, latency, memory |

---

## Known Blockers

1. **Frontend not yet functional** — Prevents testing UI interactions (watchlist, trading, chat)
2. **Chat API not yet implemented** — Prevents chat tests
3. **LiteLLM integration not yet implemented** — Prevents LLM response testing
4. **Portfolio visualization not yet built** — Prevents heatmap, chart, table tests

All API endpoints are functional (health, watchlist, portfolio, trades, streaming).

---

## Success Criteria

### Phase 4 Complete When:

✓ Test infrastructure runs end-to-end (Docker + Playwright)
✓ All smoke tests pass (API health, endpoints reachable)
✓ All feature tests pass (watchlist, trading, portfolio, chat)
✓ All error tests pass (validation, edge cases)
✓ Zero known P0 bugs
✓ < 5 P1 bugs (documented and assigned)
✓ Performance benchmarks met (< 2s load, < 100ms latency)
✓ CI/CD integration ready (GitHub Actions)

---

## Test Data Strategy

### SQLite Reset

Each test run gets a fresh SQLite database (`finally-test-data` volume is created fresh in docker-compose.test.yml).

Initial state:
- `users_profile`: id="default", cash_balance=10000
- `watchlist`: 10 default tickers
- `positions`: empty
- `trades`: empty
- `portfolio_snapshots`: empty (or one initial snapshot with value=10000)
- `chat_messages`: empty

### Deterministic Mock LLM

With `LLM_MOCK=true`:
- Chat endpoint always returns a hardcoded response
- Example: `{"message": "I suggest buying AAPL", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}], "watchlist_changes": []}`
- Enables fast, repeatable tests without API calls

### Price Simulation

Market data simulator always starts from the same seed prices (from `app/market/seed_prices.py`):
- AAPL: ~190
- GOOGL: ~175
- MSFT: ~420
- etc.

Ensures consistent starting point for all test runs.

---

## Reports & Artifacts

### Generated After Each Test Run

- **HTML Report**: `test-results/index.html` — Visual overview with timelines, screenshots, videos
- **JUnit XML**: `test-results.xml` — For CI integrations (GitHub Actions, etc.)
- **JSON Report**: `test-results.json` — Structured data for programmatic analysis
- **Traces**: `test-results/traces/` — Full Playwright traces for debugging
- **Screenshots**: Auto-captured on failure
- **Videos**: Recorded for failed tests (configured in `playwright.config.ts`)

### View Locally

```bash
npx playwright show-report
```

Opens interactive HTML dashboard showing all test results with videos and traces.

---

## Appendix: Running Individual Test Specs

```bash
# All tests
npm run test

# Only smoke tests
npx playwright test smoke

# Only watchlist tests
npx playwright test watchlist

# Pattern matching (e.g., all "buy" tests)
npx playwright test --grep "buy"

# Debug mode
npm run test:debug

# UI mode (interactive)
npm run test:ui

# Specific test by name
npx playwright test -g "Buy shares decreases cash balance"
```

---

## Appendix: Debugging in Docker

If tests fail in Docker but pass locally:

```bash
# Get logs from API container
docker compose -f test/docker-compose.test.yml logs api

# Get logs from Playwright container
docker compose -f test/docker-compose.test.yml logs playwright

# Keep containers running for inspection
docker compose -f test/docker-compose.test.yml up --build
# In another terminal:
docker compose -f test/docker-compose.test.yml logs -f api
# Manually run Playwright
docker compose -f test/docker-compose.test.yml run playwright npm run test:headed
```

---

## Summary

**Phase 4 E2E Testing is infrastructure-ready.** Smoke tests pass. All test spec templates are created and documented. Full test suite will execute as soon as Phase 3 (Frontend + Chat API) completes. Bug triage process is documented and ready to deploy.

**Next Steps**:
1. Phase 3 team finishes frontend and chat API
2. Remove placeholder comments from test specs (`test/specs/*.spec.ts`)
3. Fill in actual selectors and assertions as UI components become available
4. Run full test suite and triage bugs
5. Integrate into GitHub Actions CI/CD
