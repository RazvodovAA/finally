import { test, expect } from '@playwright/test';

test.describe('Portfolio Visualization', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/FinAlly/i);
  });

  test('portfolio displays initial state', async ({ request }) => {
    const response = await request.get('/api/portfolio');
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data.cash_balance).toBe(10000);
    expect(data.positions.length).toBe(0);
    expect(data.total_value).toBe(10000);
    expect(data.unrealized_pnl).toBe(0);
  });

  test('portfolio header shows total value', async ({ page }) => {
    // TODO: Once frontend header is built
    // - Verify portfolio total value displayed (e.g., "$10,000.00")
    // - Verify value updates as prices change (live updates via SSE)
  });

  test('portfolio header shows cash balance', async ({ page }) => {
    // TODO: Once frontend header is built
    // - Verify cash balance displayed (e.g., "$10,000.00")
    // - Verify value updates after trades execute
  });

  test('portfolio header shows connection status', async ({ page }) => {
    // TODO: Once frontend header is built
    // - Verify connection indicator visible
    // - Verify indicator is green initially (connected)
    // - Verify indicator changes to yellow when backend is unreachable
    // - Verify indicator returns to green when reconnected
  });

  test('heatmap renders with positions', async ({ page, request }) => {
    // TODO: Once frontend heatmap is built
    // - Buy some shares to create positions
    // - Verify heatmap renders (treemap visualization)
    // - Verify correct number of rectangles (one per position)
    // - Verify each rectangle shows ticker label
  });

  test('heatmap rectangle sizes proportional to weight', async ({ page, request }) => {
    // TODO: Once frontend and positions exist
    // - Buy different quantities of different stocks
    // - Verify larger positions have larger rectangles
    // - Verify sizes are proportional to portfolio weight
  });

  test('heatmap colors reflect P&L', async ({ page, request }) => {
    // TODO: Once frontend and positions exist with price movement
    // - Buy position that goes up in value (green)
    // - Buy position that goes down in value (red)
    // - Verify colors are correct
    // - Verify breakeven position is gray/neutral
  });

  test('positions table displays all columns', async ({ page }) => {
    // TODO: Once frontend table is built
    // - Buy some shares
    // - Verify table is visible
    // - Verify columns: Ticker, Quantity, Avg Cost, Current Price, P&L ($), P&L (%)
    // - Verify all values are populated correctly
  });

  test('positions table updates on price changes', async ({ page }) => {
    // TODO: Once frontend table and SSE are integrated
    // - Buy shares
    // - Wait for price updates via SSE
    // - Verify P&L values update in table
  });

  test('positions table updates on new trades', async ({ page, request }) => {
    // TODO: Once frontend table is built
    // - Buy first ticker
    // - Verify row appears in table
    // - Buy second ticker
    // - Verify second row appears
    // - Sell first ticker completely
    // - Verify first row disappears
  });

  test('empty positions shows placeholder', async ({ page }) => {
    // TODO: Once frontend table is built
    // - On fresh start with no positions
    // - Verify empty state message (e.g., "No positions yet")
    // - Execute a buy
    // - Verify empty state disappears and table appears
  });

  test('P&L chart renders with portfolio history', async ({ page }) => {
    // TODO: Once frontend chart and portfolio snapshots are implemented
    // - Execute a trade
    // - Wait for portfolio snapshot to be recorded
    // - Verify chart renders (line chart)
    // - Verify has initial data point (at page load)
    // - Verify has data point after trade
  });

  test('P&L chart shows portfolio value over time', async ({ page, request }) => {
    // TODO: Once frontend chart is built and market data is moving
    // - Wait for prices to change (simulator updates)
    // - Verify chart line shows value changes
    // - Verify X-axis is time, Y-axis is portfolio value
    // - Verify chart updates in real-time
  });

  test('P&L chart empty state', async ({ page }) => {
    // TODO: Once frontend chart is built
    // - On fresh start, might have no history
    // - Verify empty state message or placeholder chart
  });

  test('portfolio value matches sum of components', async ({ request }) => {
    // Get portfolio
    const response = await request.get('/api/portfolio');
    const data = await response.json();

    // Total value should equal cash + sum of position values
    const positionValue = data.positions.reduce(
      (sum: number, pos: any) => sum + (pos.quantity * pos.price),
      0
    );
    const expectedTotal = data.cash_balance + positionValue;
    expect(data.total_value).toBeCloseTo(expectedTotal, 2);
  });

  test('unrealized P&L is calculated correctly', async ({ request }) => {
    // Buy some shares
    const watchlist = await request.get('/api/watchlist');
    const watchlistData = await watchlist.json();
    const aaplItem = watchlistData.watchlist.find((item: any) => item.ticker === 'AAPL');
    const initialPrice = aaplItem.price;

    await request.post('/api/portfolio/trade', {
      data: { ticker: 'AAPL', side: 'buy', quantity: 10 },
    });

    // Get portfolio with position
    const portfolio = await request.get('/api/portfolio');
    const data = await portfolio.json();
    const aaplPos = data.positions.find((p: any) => p.ticker === 'AAPL');

    // Unrealized P&L = (current price - avg cost) * quantity
    const expectedPnL = (aaplPos.price - aaplPos.avg_cost) * aaplPos.quantity;
    expect(aaplPos.unrealized_pnl).toBeCloseTo(expectedPnL, 2);
  });

  test('portfolio history endpoint', async ({ request }) => {
    // TODO: Once portfolio history endpoint is implemented
    // GET /api/portfolio/history
    // - Should return array of snapshots
    // - Each snapshot: { total_value, recorded_at }
    // - Should have at least one snapshot (initial state)
    // - Should have new snapshots after trades
  });
});
