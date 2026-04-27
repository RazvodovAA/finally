'use client';

import { useMemo } from 'react';
import { Position } from '../types';

interface PortfolioHeatmapProps {
  positions: Position[];
  totalValue: number;
}

interface RectData {
  ticker: string;
  weight: number;
  pnlPercent: number;
  pnl: number;
  quantity: number;
}

export function PortfolioHeatmap({ positions, totalValue }: PortfolioHeatmapProps) {
  const rects = useMemo(() => {
    if (totalValue === 0 || positions.length === 0) {
      return [];
    }

    return positions
      .map((pos) => ({
        ticker: pos.ticker,
        weight: (pos.quantity * pos.current_price) / totalValue,
        pnlPercent: pos.pnl_percent,
        pnl: pos.unrealized_pnl,
        quantity: pos.quantity,
      }))
      .sort((a, b) => b.weight - a.weight);
  }, [positions, totalValue]);

  const getColor = (pnlPercent: number): string => {
    if (pnlPercent > 5) return '#238636';
    if (pnlPercent > 0) return '#1f6feb';
    if (pnlPercent > -5) return '#d29922';
    return '#da3633';
  };

  if (rects.length === 0) {
    return (
      <div className="terminal-panel p-8 text-center h-full flex items-center justify-center">
        <div className="text-terminal-muted">
          <p className="text-sm font-mono">No positions in portfolio</p>
          <p className="text-xs text-terminal-muted/60 mt-2">Add positions to view heatmap</p>
        </div>
      </div>
    );
  }

  return (
    <div className="terminal-panel p-4">
      <h3 className="ticker-label text-accent-yellow mb-4 text-sm">Position Heatmap</h3>
      <div
        className="grid gap-1 auto-fit"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(80px, 1fr))',
          gridAutoRows: 'minmax(80px, auto)',
        }}
      >
        {rects.map((rect) => (
          <div
            key={rect.ticker}
            className="treemap-rect p-2 flex flex-col justify-between text-xs border border-terminal-border/50"
            style={{
              backgroundColor: getColor(rect.pnlPercent),
              opacity: 0.85,
            }}
          >
            <div className="font-bold text-terminal-dark ticker-label">{rect.ticker}</div>
            <div className="text-terminal-dark">
              <div className="text-xs font-semibold">{(rect.weight * 100).toFixed(1)}%</div>
              <div className={`text-xs ${rect.pnl >= 0 ? 'font-semibold' : ''}`}>
                {rect.pnlPercent >= 0 ? '+' : ''}
                {rect.pnlPercent.toFixed(1)}%
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
