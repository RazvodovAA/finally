export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  change: number;
  change_percent: number;
  direction: 'up' | 'down' | 'flat';
  timestamp: string;
}

export interface WatchlistItem {
  ticker: string;
  price: number;
  change: number;
  change_percent: number;
  direction: 'up' | 'down' | 'flat';
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

export interface PortfolioResponse {
  positions: Position[];
  cash_balance: number;
  total_value: number;
  total_unrealized_pnl: number;
}

export interface HistoryItem {
  timestamp: string;
  total_value: number;
}

export interface ConnectionStatus {
  status: 'connected' | 'reconnecting' | 'disconnected';
  message: string;
}

export interface SparklinePoint {
  timestamp: string;
  price: number;
}
