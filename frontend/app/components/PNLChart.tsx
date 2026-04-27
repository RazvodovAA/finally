'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { HistoryItem } from '../types';

interface PNLChartProps {
  data: HistoryItem[];
}

export function PNLChart({ data }: PNLChartProps) {
  const formattedData = data.map((item) => ({
    timestamp: new Date(item.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    }),
    value: item.total_value,
  }));

  const minValue = Math.min(...data.map((d) => d.total_value), 10000);
  const maxValue = Math.max(...data.map((d) => d.total_value), 10000);
  const domain = [minValue * 0.99, maxValue * 1.01];

  return (
    <div className="terminal-panel p-4 h-full">
      <h3 className="ticker-label text-accent-yellow mb-4 text-sm">Portfolio Value</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formattedData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" vertical={false} />
          <XAxis
            dataKey="timestamp"
            stroke="#8b949e"
            style={{ fontSize: '12px' }}
            tick={{ fill: '#8b949e' }}
          />
          <YAxis
            stroke="#8b949e"
            style={{ fontSize: '12px' }}
            tick={{ fill: '#8b949e' }}
            domain={domain}
            tickFormatter={(value) => `$${(value / 1000).toFixed(1)}k`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1a1a2e',
              border: '1px solid #30363d',
              borderRadius: '4px',
            }}
            labelStyle={{ color: '#c9d1d9' }}
            formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Value']}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#209dd7"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
