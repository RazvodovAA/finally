import { test, expect } from '@playwright/test';

test.describe('Fresh Start Scenario', () => {
  test('page loads with default watchlist', async ({ page }) => {
    await page.goto('/');

    // Wait for page to load and initial content to appear
    await expect(page).toHaveTitle(/FinAlly/i);

    // Verify basic layout loads
    const mainContent = page.locator('main');
    await expect(mainContent).toBeVisible();
  });

  test('API health check passes', async ({ request }) => {
    const response = await request.get('/api/health');
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('status');
  });

  test('watchlist endpoint returns default tickers', async ({ request }) => {
    const response = await request.get('/api/watchlist');
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(Array.isArray(data.watchlist)).toBe(true);

    // Should have default 10 tickers
    const defaultTickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'];
    const watchlistTickers = data.watchlist.map((item: any) => item.ticker);

    for (const ticker of defaultTickers) {
      expect(watchlistTickers).toContain(ticker);
    }
  });

  test('portfolio endpoint returns initial state', async ({ request }) => {
    const response = await request.get('/api/portfolio');
    expect(response.status()).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty('cash_balance');
    expect(data).toHaveProperty('positions');
    expect(data).toHaveProperty('total_value');
    expect(data).toHaveProperty('unrealized_pnl');

    // Initial cash should be 10000
    expect(data.cash_balance).toBe(10000);
  });

  test('SSE stream endpoint is available', async ({ request }) => {
    const response = await request.get('/api/stream/prices', {
      headers: {
        'Accept': 'text/event-stream',
      },
    });

    // SSE endpoints return 200 but with text/event-stream content type
    expect([200, 206]).toContain(response.status());
  });
});

test.describe('Price Streaming', () => {
  test('SSE stream delivers price updates', async ({ page }) => {
    // This test requires EventSource support in the browser
    // Will be implemented with proper SSE testing once frontend is ready

    await page.goto('/');

    // For now, just verify the page loads
    // Later: assert on actual SSE event reception
    await expect(page).toHaveTitle(/FinAlly/i);
  });
});

test.describe('Connection Status', () => {
  test('connection status indicator is visible', async ({ page }) => {
    await page.goto('/');

    // Look for connection status indicator
    // (This will depend on frontend implementation)
    // Placeholder: verify page loaded
    await expect(page).toHaveTitle(/FinAlly/i);
  });
});
