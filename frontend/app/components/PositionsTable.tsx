'use client';

import { Position } from '../types';

interface PositionsTableProps {
  positions: Position[];
}

export function PositionsTable({ positions }: PositionsTableProps) {
  return (
    <div className="terminal-panel rounded overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="grid-header border-b border-terminal-border">
              <th className="px-4 py-3 text-left ticker-label text-accent-yellow">Ticker</th>
              <th className="px-4 py-3 text-right price-cell">Quantity</th>
              <th className="px-4 py-3 text-right price-cell">Avg Cost</th>
              <th className="px-4 py-3 text-right price-cell">Current Price</th>
              <th className="px-4 py-3 text-right price-cell">Unrealized P&L</th>
              <th className="px-4 py-3 text-right price-cell">Return %</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-terminal-muted">
                  No positions yet. Start trading to build your portfolio.
                </td>
              </tr>
            ) : (
              positions.map((position) => (
                <tr
                  key={position.ticker}
                  className="border-b border-terminal-border hover:bg-terminal-bg/50 transition-colors"
                >
                  <td className="px-4 py-3 ticker-label text-accent-yellow">{position.ticker}</td>
                  <td className="px-4 py-3 price-cell">{position.quantity.toFixed(2)}</td>
                  <td className="px-4 py-3 price-cell">
                    ${position.avg_cost.toLocaleString('en-US', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td className="px-4 py-3 price-cell">
                    ${position.current_price.toLocaleString('en-US', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td
                    className={`px-4 py-3 price-cell font-semibold ${
                      position.unrealized_pnl >= 0 ? 'text-price-up' : 'text-price-down'
                    }`}
                  >
                    ${position.unrealized_pnl.toLocaleString('en-US', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td
                    className={`px-4 py-3 price-cell font-semibold ${
                      position.pnl_percent >= 0 ? 'text-price-up' : 'text-price-down'
                    }`}
                  >
                    {position.pnl_percent >= 0 ? '+' : ''}{position.pnl_percent.toFixed(2)}%
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
