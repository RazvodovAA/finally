'use client';

import { useState, useEffect, memo } from 'react';
import { WatchlistItem, PriceUpdate, SparklinePoint } from '../types';
import { Sparkline } from './Sparkline';

interface WatchlistGridProps {
  watchlist: WatchlistItem[];
  prices: Record<string, PriceUpdate>;
  onSelectTicker: (ticker: string) => void;
  selectedTicker?: string;
}

function WatchlistGridComponent({
  watchlist,
  prices,
  onSelectTicker,
  selectedTicker,
}: WatchlistGridProps) {
  const [sparklines, setSparklines] = useState<Record<string, SparklinePoint[]>>({});
  const [flashingCells, setFlashingCells] = useState<Record<string, string>>({});

  useEffect(() => {
    watchlist.forEach((item) => {
      setSparklines((prev) => ({
        ...prev,
        [item.ticker]: prev[item.ticker] || [],
      }));
    });
  }, [watchlist]);

  useEffect(() => {
    const timers: NodeJS.Timeout[] = [];
    Object.entries(prices).forEach(([ticker, priceUpdate]) => {
      setSparklines((prev) => {
        if (!prev[ticker]) {
          return prev;
        }
        const current = [...prev[ticker]];
        current.push({
          timestamp: priceUpdate.timestamp,
          price: priceUpdate.price,
        });

        if (current.length > 100) {
          current.shift();
        }

        return {
          ...prev,
          [ticker]: current,
        };
      });

      const direction = priceUpdate.direction;
      if (direction !== 'flat') {
        setFlashingCells((prev) => ({
          ...prev,
          [ticker]: direction,
        }));

        const timer = setTimeout(() => {
          setFlashingCells((prev) => {
            const updated = { ...prev };
            delete updated[ticker];
            return updated;
          });
        }, 500);
        timers.push(timer);
      }
    });

    return () => {
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [prices]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2 p-4 bg-terminal-bg border border-terminal-border rounded">
      {watchlist.map((item) => {
        const isFlashing = flashingCells[item.ticker];
        const sparklineData = sparklines[item.ticker] || [];

        return (
          <div
            key={item.ticker}
            onClick={() => onSelectTicker(item.ticker)}
            className={`
              terminal-panel p-3 cursor-pointer hover-lift group
              ${selectedTicker === item.ticker ? 'ring-2 ring-accent-blue' : ''}
              ${isFlashing ? (isFlashing === 'up' ? 'price-flash-up' : 'price-flash-down') : ''}
            `}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="ticker-label text-accent-yellow">{item.ticker}</div>
              <div
                className={`text-xs font-semibold ${
                  item.direction === 'up'
                    ? 'text-price-up'
                    : item.direction === 'down'
                      ? 'text-price-down'
                      : 'text-terminal-muted'
                }`}
              >
                {item.direction === 'up' ? '↑' : item.direction === 'down' ? '↓' : '→'}
              </div>
            </div>

            <div className="price-cell text-lg font-bold text-accent-blue mb-1">
              ${item.price.toFixed(2)}
            </div>

            <div
              className={`text-xs font-mono ${
                item.direction === 'up'
                  ? 'text-price-up'
                  : item.direction === 'down'
                    ? 'text-price-down'
                    : 'text-terminal-muted'
              }`}
            >
              {item.direction === 'up' ? '+' : ''}{item.change_percent.toFixed(2)}%
            </div>

            {sparklineData.length > 1 && (
              <div className="mt-2 pt-2 border-t border-terminal-border/50">
                <Sparkline
                  data={sparklineData}
                  width={100}
                  height={24}
                  className="w-full"
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export const WatchlistGrid = memo(WatchlistGridComponent);
