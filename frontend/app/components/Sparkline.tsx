'use client';

import { useMemo } from 'react';
import { SparklinePoint } from '../types';

interface SparklineProps {
  data: SparklinePoint[];
  width?: number;
  height?: number;
  className?: string;
}

export function Sparkline({ data, width = 100, height = 30, className = '' }: SparklineProps) {
  const { points, min, max, pathD } = useMemo(() => {
    if (data.length === 0) {
      return { points: [], min: 0, max: 0, pathD: '' };
    }

    const prices = data.map((d) => d.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;

    const padding = 2;
    const chartWidth = width - padding * 2;
    const chartHeight = height - padding * 2;

    const points = data.map((d, i) => {
      const x = padding + (i / (data.length - 1 || 1)) * chartWidth;
      const y = padding + chartHeight - ((d.price - min) / range) * chartHeight;
      return { x, y };
    });

    let pathD = '';
    if (points.length > 0) {
      pathD = `M ${points[0].x} ${points[0].y}`;
      for (let i = 1; i < points.length; i++) {
        pathD += ` L ${points[i].x} ${points[i].y}`;
      }
    }

    return { points, min, max, pathD };
  }, [data, width, height]);

  const isPositive = data.length > 1 ? data[data.length - 1].price >= data[0].price : true;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      style={{ overflow: 'visible' }}
    >
      <path
        d={pathD}
        stroke={isPositive ? '#238636' : '#da3633'}
        strokeWidth="1.5"
        fill="none"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
