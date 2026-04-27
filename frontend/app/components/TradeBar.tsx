'use client';

import { useState } from 'react';

interface TradeBarProps {
  onBuy: (ticker: string, quantity: number) => Promise<void>;
  onSell: (ticker: string, quantity: number) => Promise<void>;
  disabled?: boolean;
}

export function TradeBar({ onBuy, onSell, disabled = false }: TradeBarProps) {
  const [ticker, setTicker] = useState('');
  const [quantity, setQuantity] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleTrade = async (side: 'buy' | 'sell') => {
    if (!ticker.trim() || !quantity.trim()) {
      setError('Please fill in all fields');
      return;
    }

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      setError('Quantity must be a positive number');
      return;
    }

    setError('');
    setLoading(true);

    try {
      if (side === 'buy') {
        await onBuy(ticker.toUpperCase(), qty);
      } else {
        await onSell(ticker.toUpperCase(), qty);
      }
      setTicker('');
      setQuantity('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trade failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="terminal-panel p-4">
      <h3 className="ticker-label text-accent-yellow mb-4 text-sm">Trade Execution</h3>

      <div className="grid grid-cols-12 gap-3">
        <input
          type="text"
          placeholder="AAPL"
          value={ticker}
          onChange={(e) => {
            setTicker(e.target.value);
            setError('');
          }}
          disabled={disabled || loading}
          className="col-span-3"
        />

        <input
          type="number"
          placeholder="Quantity"
          value={quantity}
          onChange={(e) => {
            setQuantity(e.target.value);
            setError('');
          }}
          disabled={disabled || loading}
          step="0.01"
          min="0"
          className="col-span-3"
        />

        <button
          onClick={() => handleTrade('buy')}
          disabled={disabled || loading || !ticker.trim() || !quantity.trim()}
          className="col-span-3 btn-trade btn-buy disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Processing...' : 'Buy'}
        </button>

        <button
          onClick={() => handleTrade('sell')}
          disabled={disabled || loading || !ticker.trim() || !quantity.trim()}
          className="col-span-3 btn-trade btn-sell disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Processing...' : 'Sell'}
        </button>
      </div>

      {error && (
        <div className="mt-3 p-2 bg-price-down/20 border border-price-down/50 rounded text-price-down text-xs font-mono">
          {error}
        </div>
      )}
    </div>
  );
}
