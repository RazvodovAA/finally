# FinAlly E2E Tests

End-to-end tests for the FinAlly trading workstation using Playwright.

## Setup

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local development)
- Playwright browsers installed

### Quick Start (Docker)

```bash
# Run all tests in containers
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Clean up
docker-compose -f docker-compose.test.yml down -v
```

### Local Development

```bash
# Install dependencies
npm install

# Start the backend (from project root)
docker-compose up -d

# Run tests in headed mode (see browser)
npm run test:headed

# Run tests in debug mode (interactive)
npm run test:debug

# Run tests in UI mode (interactive dashboard)
npm run test:ui

# Generate test code by interacting with app
npm run test:codegen
```

## Test Structure

```
test/
├── specs/
│   ├── smoke.spec.ts         # Basic smoke tests (page load, API health)
│   ├── watchlist.spec.ts     # Watchlist CRUD operations
│   ├── trading.spec.ts       # Buy/sell order execution
│   ├── portfolio.spec.ts     # Portfolio visualization and stats
│   ├── chat.spec.ts          # LLM chat integration
│   ├── sse.spec.ts           # SSE streaming resilience
│   └── error.spec.ts         # Error handling edge cases
├── fixtures/                 # Shared test utilities (TBD)
├── docker-compose.test.yml   # Test infrastructure
├── playwright.config.ts      # Playwright configuration
└── README.md
```

## Test Categories

### Smoke Tests (`smoke.spec.ts`)
- Page loads with title
- API health check
- Watchlist endpoint returns default tickers
- Portfolio endpoint returns initial state
- SSE stream is available

### Watchlist Tests (`watchlist.spec.ts`, TODO)
- Add ticker to watchlist
- Remove ticker from watchlist
- Duplicate ticker handling
- Invalid ticker handling
- Watchlist updates reflected in price stream

### Trading Tests (`trading.spec.ts`, TODO)
- Buy order execution
  - Price decreases from cash balance
  - Position appears in table
  - Portfolio updates
- Sell order execution
  - Cash increases
  - Position updates or disappears
  - Portfolio updates
- Error cases
  - Insufficient cash
  - Insufficient shares
  - Invalid ticker

### Portfolio Tests (`portfolio.spec.ts`, TODO)
- Heatmap renders with positions
- Heatmap colors (green/red for P&L)
- Heatmap sizes (proportional to weight)
- P&L chart shows portfolio value over time
- Positions table displays all columns correctly

### Chat Tests (`chat.spec.ts`, TODO)
- Send message to chat
- Receive LLM response
- Trade auto-execution from chat
- Watchlist changes from chat
- Mock LLM returns deterministic responses

### SSE Tests (`sse.spec.ts`, TODO)
- Prices update via SSE
- Flash animations on price change
- Change % displayed
- Sparklines accumulate data
- Reconnection on disconnect
- Connection status indicator states

### Error Tests (`error.spec.ts`, TODO)
- Buy without sufficient cash
- Sell without sufficient shares
- Add duplicate watchlist ticker
- Empty chat message
- Invalid form input

## Environment Variables

Tests automatically set:
- `LLM_MOCK=true` — Use deterministic mock responses instead of calling OpenAI
- `PYTHONUNBUFFERED=1` — Unbuffered Python output for better debugging

## Running Specific Tests

```bash
# Run only smoke tests
npx playwright test smoke

# Run tests matching a pattern
npx playwright test --grep "watchlist"

# Run a specific test file
npx playwright test specs/smoke.spec.ts

# Run tests with a specific tag
npx playwright test --grep @critical
```

## Debugging

### View Test Report
```bash
npx playwright show-report
```

### Debug Mode
```bash
npm run test:debug
```

### UI Mode
```bash
npm run test:ui
```

### Screenshots and Videos
Failed tests automatically capture:
- Screenshot of failure
- Video of test execution (retained on failure)
- Full trace for inspection

These are saved in `test-results/` and `test-videos/` directories.

## Performance Benchmarks

Expected metrics:
- Page load time: < 2s
- Price update latency: < 100ms from server
- Chart render: smooth (60fps)
- No memory leaks after 5min operation

(Performance tests to be added in Phase 4)

## CI/CD Integration

Tests run in CI with:
- `LLM_MOCK=true` for determinism
- 1 worker (sequential) to avoid race conditions
- 2 retries on transient failures
- Artifacts saved (HTML report, JUnit XML, traces)

## Phase 4 Roadmap

1. **Smoke tests** ✓ — Basic infrastructure, page loads, API health
2. **Watchlist tests** (pending frontend) — Add/remove/update
3. **Trading tests** (pending frontend) — Buy/sell/errors
4. **Portfolio tests** (pending frontend) — Heatmap, chart, table
5. **Chat tests** (pending chat API) — Message, response, auto-exec
6. **SSE tests** (pending SSE integration) — Stream, reconnect, animations
7. **Error tests** (pending edge case handling) — Validation, bounds
8. **Performance tests** (pending optimization) — Load time, latency, memory

## Known Limitations

- Frontend is still being built (Phase 3 in progress)
- Some test specs are placeholders pending full frontend implementation
- SSE connection testing requires full EventSource integration
- Chat testing requires LLM route implementation

## Troubleshooting

### Tests timeout waiting for API
```
Error: Timeout while connecting to http://localhost:8000
```
Ensure Docker container is running and healthy:
```bash
docker ps
docker logs finally-test-api
```

### Playwright browsers not installed
```bash
npx playwright install
```

### Port 8000 already in use
```bash
docker ps
docker kill <container-id>
```

## Contributing

When adding new tests:
1. Follow the naming convention: `test.describe` for suites, `test` for individual tests
2. Use meaningful test names (e.g., "Buy shares decreases cash balance")
3. Add comments for complex assertions
4. Tag critical tests with `@critical`
5. Update this README with test category documentation
