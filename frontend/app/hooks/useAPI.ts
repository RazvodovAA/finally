import { useCallback, useMemo } from 'react';
import { PortfolioResponse, WatchlistItem, HistoryItem } from '../types';

const API_BASE = '/api';

export function useAPI() {
  const getWatchlist = useCallback(async (): Promise<WatchlistItem[]> => {
    const res = await fetch(`${API_BASE}/watchlist`);
    if (!res.ok) throw new Error('Failed to fetch watchlist');
    return res.json();
  }, []);

  const getPortfolio = useCallback(async (): Promise<PortfolioResponse> => {
    const res = await fetch(`${API_BASE}/portfolio`);
    if (!res.ok) throw new Error('Failed to fetch portfolio');
    return res.json();
  }, []);

  const getPortfolioHistory = useCallback(async (): Promise<HistoryItem[]> => {
    const res = await fetch(`${API_BASE}/portfolio/history`);
    if (!res.ok) throw new Error('Failed to fetch portfolio history');
    return res.json();
  }, []);

  const executeTrade = useCallback(
    async (ticker: string, side: 'buy' | 'sell', quantity: number) => {
      const res = await fetch(`${API_BASE}/portfolio/trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, side, quantity }),
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Trade failed');
      }
      return res.json();
    },
    []
  );

  const addWatchlistItem = useCallback(
    async (ticker: string): Promise<WatchlistItem[]> => {
      const res = await fetch(`${API_BASE}/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
      });
      if (!res.ok) throw new Error('Failed to add to watchlist');
      return res.json();
    },
    []
  );

  const removeWatchlistItem = useCallback(async (ticker: string): Promise<WatchlistItem[]> => {
    const res = await fetch(`${API_BASE}/watchlist/${ticker}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to remove from watchlist');
    return res.json();
  }, []);

  return useMemo(
    () => ({
      getWatchlist,
      getPortfolio,
      getPortfolioHistory,
      executeTrade,
      addWatchlistItem,
      removeWatchlistItem,
    }),
    [getWatchlist, getPortfolio, getPortfolioHistory, executeTrade, addWatchlistItem, removeWatchlistItem]
  );
}
