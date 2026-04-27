import { test, expect } from '@playwright/test';

test.describe('Trade Execution', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/FinAlly/i);
  });

  test('buy order via API', async ({ request }) => {
    // Get current price
    const watchlistResponse = await request.get('/api/watchlist');
    const watchlist = await watchlistResponse.json();
    const aaplPrice = watchlist.watchlist.find((item: any) => item.ticker === 'AAPL')?.price;
    expect(aaplPrice).toBeGreaterThan(0);

    // Get initial portfolio
    const initialPortfolio = await request.get('/api/portfolio');
    const initialData = await initialPortfolio.json();
    const initialCash = initialData.cash_balance;

    // Buy 10 shares
    const tradeResponse = await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'AAPL',
        side: 'buy',
        quantity: 10,
      },
    });

    expect(tradeResponse.status()).toBe(200);
    const trade = await tradeResponse.json();
    expect(trade).toHaveProperty('id');
    expect(trade).toHaveProperty('ticker', 'AAPL');
    expect(trade).toHaveProperty('side', 'buy');
    expect(trade).toHaveProperty('quantity', 10);
    expect(trade).toHaveProperty('price', aaplPrice);

    // Verify cash decreased
    const finalPortfolio = await request.get('/api/portfolio');
    const finalData = await finalPortfolio.json();
    const expectedCash = initialCash - (10 * aaplPrice);
    expect(finalData.cash_balance).toBeCloseTo(expectedCash, 2);

    // Verify position created
    expect(finalData.positions).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          ticker: 'AAPL',
          quantity: 10,
        }),
      ])
    );
  });

  test('sell order via API', async ({ request }) => {
    // First buy some shares
    await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'GOOGL',
        side: 'buy',
        quantity: 5,
      },
    });

    // Get cash after buy
    let portfolio = await request.get('/api/portfolio');
    let data = await portfolio.json();
    const cashAfterBuy = data.cash_balance;

    // Get current price
    const watchlistResponse = await request.get('/api/watchlist');
    const watchlist = await watchlistResponse.json();
    const googlPrice = watchlist.watchlist.find((item: any) => item.ticker === 'GOOGL')?.price;

    // Sell 3 shares
    const sellResponse = await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'GOOGL',
        side: 'sell',
        quantity: 3,
      },
    });

    expect(sellResponse.status()).toBe(200);

    // Verify cash increased
    portfolio = await request.get('/api/portfolio');
    data = await portfolio.json();
    const expectedCash = cashAfterBuy + (3 * googlPrice);
    expect(data.cash_balance).toBeCloseTo(expectedCash, 2);

    // Verify position updated (should have 2 shares left)
    const googlPosition = data.positions.find((p: any) => p.ticker === 'GOOGL');
    expect(googlPosition?.quantity).toBe(2);
  });

  test('buy order via UI', async ({ page, request }) => {
    // TODO: Once frontend trade form is built
    // - Find ticker input, quantity input
    // - Enter 'MSFT' and '5'
    // - Click Buy button
    // - Verify order executes (cash decreases, position appears)
  });

  test('sell order via UI', async ({ page, request }) => {
    // TODO: Once frontend trade form is built and position exists
    // - Buy some shares first
    // - Find sell form
    // - Enter quantity
    // - Click Sell
    // - Verify position updates/deletes
  });

  test('buy with insufficient cash', async ({ request }) => {
    // Try to buy 100000 shares of expensive stock
    const response = await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'NVDA',
        side: 'buy',
        quantity: 100000,
      },
    });

    // Expect 400 or 422 error
    expect([400, 422]).toContain(response.status());

    // Verify no trade was executed
    const portfolio = await request.get('/api/portfolio');
    const data = await portfolio.json();
    expect(data.cash_balance).toBe(10000); // Unchanged
    expect(data.positions.length).toBe(0); // No positions
  });

  test('sell with insufficient shares', async ({ request }) => {
    // Try to sell shares we don't have
    const response = await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'TSLA',
        side: 'sell',
        quantity: 1,
      },
    });

    // Expect 400 or 422 error
    expect([400, 422]).toContain(response.status());
  });

  test('sell all shares', async ({ request }) => {
    // Buy 10 shares
    await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'META',
        side: 'buy',
        quantity: 10,
      },
    });

    // Sell all 10
    const sellResponse = await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'META',
        side: 'sell',
        quantity: 10,
      },
    });

    expect(sellResponse.status()).toBe(200);

    // Verify position is gone
    const portfolio = await request.get('/api/portfolio');
    const data = await portfolio.json();
    const metaPosition = data.positions.find((p: any) => p.ticker === 'META');
    expect(metaPosition).toBeUndefined();
  });

  test('buy with exact cash balance', async ({ request }) => {
    // Get a cheap stock price (e.g., JPM around $190)
    const watchlistResponse = await request.get('/api/watchlist');
    const watchlist = await watchlistResponse.json();
    const jpmPrice = watchlist.watchlist.find((item: any) => item.ticker === 'JPM')?.price;

    // Calculate quantity to use exactly all cash
    const quantity = Math.floor(10000 / jpmPrice);

    const response = await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'JPM',
        side: 'buy',
        quantity,
      },
    });

    expect(response.status()).toBe(200);

    // Verify cash is near zero
    const portfolio = await request.get('/api/portfolio');
    const data = await portfolio.json();
    expect(data.cash_balance).toBeLessThan(1); // Allow for rounding
  });

  test('rapid successive trades', async ({ request }) => {
    // Buy, then sell, then buy again in quick succession
    const trades = [
      { side: 'buy', quantity: 5 },
      { side: 'sell', quantity: 2 },
      { side: 'buy', quantity: 3 },
      { side: 'sell', quantity: 6 },
    ];

    let position = 0;
    for (const trade of trades) {
      const response = await request.post('/api/portfolio/trade', {
        data: {
          ticker: 'V',
          side: trade.side,
          quantity: trade.quantity,
        },
      });

      expect([200, 400, 422]).toContain(response.status());

      if (trade.side === 'buy' && response.status() === 200) {
        position += trade.quantity;
      } else if (trade.side === 'sell' && response.status() === 200) {
        position -= trade.quantity;
      }
    }

    // Verify final position matches
    const portfolio = await request.get('/api/portfolio');
    const data = await portfolio.json();
    const vPosition = data.positions.find((p: any) => p.ticker === 'V');
    expect(vPosition?.quantity ?? 0).toBe(Math.max(0, position));
  });

  test('trade history recorded', async ({ request }) => {
    // Execute a trade
    await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'NFLX',
        side: 'buy',
        quantity: 2,
      },
    });

    // TODO: Once history endpoint is implemented
    // GET /api/portfolio/trades or similar
    // - Verify trade appears in history
    // - Verify all fields are correct (ticker, side, quantity, price, timestamp)
  });

  test('portfolio total value updates after trade', async ({ request }) => {
    // Get initial total value
    let portfolio = await request.get('/api/portfolio');
    let data = await portfolio.json();
    const initialTotal = data.total_value;

    // Execute a buy
    await request.post('/api/portfolio/trade', {
      data: {
        ticker: 'AMZN',
        side: 'buy',
        quantity: 10,
      },
    });

    // Get new total value
    portfolio = await request.get('/api/portfolio');
    data = await portfolio.json();
    const finalTotal = data.total_value;

    // Total should have changed (now includes position + cash)
    expect(finalTotal).not.toEqual(initialTotal);

    // Total should be sum of cash + position value
    const expectedTotal = data.cash_balance + (10 * data.positions[0]?.price || 0);
    expect(finalTotal).toBeCloseTo(expectedTotal, 2);
  });
});
