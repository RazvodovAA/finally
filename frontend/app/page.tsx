'use client';

import { useEffect, useState, useCallback } from 'react';
import { Header } from './components/Header';
import { WatchlistGrid } from './components/WatchlistGrid';
import { PositionsTable } from './components/PositionsTable';
import { TradeBar } from './components/TradeBar';
import { PriceChart } from './components/PriceChart';
import { PNLChart } from './components/PNLChart';
import { PortfolioHeatmap } from './components/PortfolioHeatmap';
import { ChatPanel } from './components/ChatPanel';
import { useSSE } from './hooks/useSSE';
import { useAPI } from './hooks/useAPI';
import { WatchlistItem, PortfolioResponse, HistoryItem, SparklinePoint } from './types';

export default function Home() {
  const { prices, connectionStatus } = useSSE();
  const api = useAPI();

  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioResponse>({
    positions: [],
    cash_balance: 10000,
    total_value: 10000,
    total_unrealized_pnl: 0,
  });
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedTicker, setSelectedTicker] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [watchlistData, portfolioData, historyData] = await Promise.all([
        api.getWatchlist(),
        api.getPortfolio(),
        api.getPortfolioHistory(),
      ]);

      setWatchlist(watchlistData);
      setPortfolio(portfolioData);
      setHistory(historyData);
      setSelectedTicker(watchlistData[0]?.ticker);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);


  const handleBuy = useCallback(
    async (ticker: string, quantity: number) => {
      await api.executeTrade(ticker, 'buy', quantity);
      await loadInitialData();
    },
    [api, loadInitialData]
  );

  const handleSell = useCallback(
    async (ticker: string, quantity: number) => {
      await api.executeTrade(ticker, 'sell', quantity);
      await loadInitialData();
    },
    [api, loadInitialData]
  );


  return (
    <div className="min-h-screen bg-terminal-dark">
      <Header
        totalValue={portfolio.total_value}
        cashBalance={portfolio.cash_balance}
        connectionStatus={connectionStatus}
      />

      <main className="flex gap-0 h-[calc(100vh-80px)]">
        <div className="flex-1 overflow-auto flex flex-col">
          <div className="p-4">
            {error && (
              <div className="mb-4 p-3 bg-price-down/20 border border-price-down/50 rounded text-price-down text-sm font-mono">
                {error}
              </div>
            )}

            {loading ? (
              <div className="text-center py-12 text-terminal-muted">
                <p className="text-sm font-mono">Loading dashboard...</p>
              </div>
            ) : (
              <>
                <div className="mb-4">
                  <WatchlistGrid
                    watchlist={watchlist}
                    prices={prices}
                    onSelectTicker={setSelectedTicker}
                    selectedTicker={selectedTicker}
                  />
                </div>

                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="col-span-2">
                    {selectedTicker && (
                      <PriceChart ticker={selectedTicker} prices={prices} />
                    )}
                  </div>
                  <div>
                    <PortfolioHeatmap
                      positions={portfolio.positions}
                      totalValue={portfolio.total_value}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="col-span-2">
                    <PNLChart data={history} />
                  </div>
                  <div>
                    <TradeBar
                      onBuy={handleBuy}
                      onSell={handleSell}
                      disabled={connectionStatus.status === 'disconnected'}
                    />
                  </div>
                </div>

                <div className="mb-4">
                  <PositionsTable positions={portfolio.positions} />
                </div>
              </>
            )}
          </div>
        </div>

        <div className="w-80 border-l border-terminal-border bg-terminal-bg">
          <ChatPanel isOpen={true} />
        </div>
      </main>
    </div>
  );
}
