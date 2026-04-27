import { test, expect } from '@playwright/test';

test.describe('Watchlist Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/FinAlly/i);
  });

  test('add ticker to watchlist via UI', async ({ page }) => {
    // TODO: Once frontend is built
    // - Find add ticker input/button
    // - Type 'PYPL'
    // - Click Add
    // - Verify PYPL appears in watchlist with live price
    // - Verify price updates via SSE
  });

  test('remove ticker from watchlist via UI', async ({ page }) => {
    // TODO: Once frontend is built
    // - Find remove button for a ticker (e.g., NFLX)
    // - Click remove
    // - Verify ticker disappears from watchlist
    // - Verify simulator stops tracking (if not in positions)
  });

  test('add ticker via API', async ({ request }) => {
    // Add ticker via REST API
    const response = await request.post('/api/watchlist', {
      data: { ticker: 'PYPL' },
    });

    expect(response.status()).toBe(201);
    const data = await response.json();
    expect(data).toHaveProperty('id');
    expect(data).toHaveProperty('ticker', 'PYPL');

    // Verify it appears in watchlist
    const getResponse = await request.get('/api/watchlist');
    const watchlist = await getResponse.json();
    const tickers = watchlist.watchlist.map((item: any) => item.ticker);
    expect(tickers).toContain('PYPL');
  });

  test('remove ticker via API', async ({ request }) => {
    // First add a ticker
    await request.post('/api/watchlist', {
      data: { ticker: 'ADBE' },
    });

    // Then remove it
    const deleteResponse = await request.delete('/api/watchlist/ADBE');
    expect(deleteResponse.status()).toBe(200);

    // Verify it's gone
    const getResponse = await request.get('/api/watchlist');
    const watchlist = await getResponse.json();
    const tickers = watchlist.watchlist.map((item: any) => item.ticker);
    expect(tickers).not.toContain('ADBE');
  });

  test('duplicate ticker handling', async ({ request }) => {
    // Try to add AAPL (already in default watchlist)
    const response = await request.post('/api/watchlist', {
      data: { ticker: 'AAPL' },
    });

    // Should either error (409) or silently succeed (201)
    // depending on implementation choice
    expect([201, 409]).toContain(response.status());
  });

  test('add non-existent ticker', async ({ request }) => {
    // Try to add a made-up ticker
    const response = await request.post('/api/watchlist', {
      data: { ticker: 'FAKECO' },
    });

    // Behavior TBD: either allow (simulator will track) or reject (400)
    // For now, expect success (simulator can track any ticker)
    if (response.status() === 201) {
      const data = await response.json();
      expect(data.ticker).toBe('FAKECO');
    }
  });

  test('watchlist persists after page reload', async ({ page, request }) => {
    // Add ticker via API
    await request.post('/api/watchlist', {
      data: { ticker: 'INTC' },
    });

    // Reload page
    await page.reload();
    await expect(page).toHaveTitle(/FinAlly/i);

    // TODO: Once frontend is built
    // - Verify INTC is still in watchlist
  });
});
