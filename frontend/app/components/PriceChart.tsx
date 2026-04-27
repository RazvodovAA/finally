'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { SparklinePoint, PriceUpdate } from '../types';
import { useState, useEffect, memo } from 'react';

interface PriceChartProps {
  ticker: string;
  prices?: Record<string, PriceUpdate>;
}

function PriceChartComponent({ ticker, prices = {} }: PriceChartProps) {
  const [data, setData] = useState<SparklinePoint[]>([]);

  useEffect(() => {
    const priceUpdate = prices[ticker];
    if (priceUpdate) {
      setData((prev) => {
        const current = [...prev];
        current.push({
          timestamp: priceUpdate.timestamp,
          price: priceUpdate.price,
        });
        if (current.length > 100) {
          current.shift();
        }
        return current;
      });
    }
  }, [prices, ticker]);

  const formattedData = data.map((item) => ({
    time: new Date(item.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }),
    price: item.price,
  }));

  if (formattedData.length < 2) {
    return (
      <div className="terminal-panel p-4 h-full flex items-center justify-center">
        <div className="text-terminal-muted text-sm">Awaiting price data for {ticker}...</div>
      </div>
    );
  }

  const priceValues = data.map((d) => d.price);
  const minPrice = Math.min(...priceValues);
  const maxPrice = Math.max(...priceValues);
  const range = maxPrice - minPrice || 1;
  const domain = [minPrice - range * 0.05, maxPrice + range * 0.05];

  const isPositive = data[data.length - 1].price >= data[0].price;

  return (
    <div className="terminal-panel p-4 h-full">
      <h3 className="ticker-label text-accent-yellow mb-4 text-sm">{ticker} Price</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formattedData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" vertical={false} />
          <XAxis
            dataKey="time"
            stroke="#8b949e"
            style={{ fontSize: '12px' }}
            tick={{ fill: '#8b949e' }}
          />
          <YAxis
            stroke="#8b949e"
            style={{ fontSize: '12px' }}
            tick={{ fill: '#8b949e' }}
            domain={domain}
            tickFormatter={(value) => `$${value.toFixed(2)}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid #30363d',
              borderRadius: '4px',
            }}
            labelStyle={{ color: '#c9d1d9' }}
            formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Price']}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke={isPositive ? '#238636' : '#da3633'}
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export const PriceChart = memo(PriceChartComponent);
