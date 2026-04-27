'use client';

import { ConnectionStatus } from '../types';

interface HeaderProps {
  totalValue: number;
  cashBalance: number;
  connectionStatus: ConnectionStatus;
}

export function Header({ totalValue, cashBalance, connectionStatus }: HeaderProps) {
  const getStatusColor = () => {
    switch (connectionStatus.status) {
      case 'connected':
        return 'bg-price-up';
      case 'reconnecting':
        return 'bg-accent-yellow';
      case 'disconnected':
        return 'bg-price-down';
    }
  };

  return (
    <header className="bg-terminal-bg border-b border-terminal-border sticky top-0 z-50">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-xl font-bold text-accent-yellow ticker-label">FinAlly</h1>
            <p className="text-xs text-terminal-muted">AI Trading Workstation</p>
          </div>
        </div>

        <div className="flex items-center gap-8">
          <div className="text-right">
            <div className="text-xs text-terminal-muted uppercase tracking-wider">Total Portfolio Value</div>
            <div className="text-2xl font-bold text-accent-blue price-cell">
              ${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          <div className="border-l border-terminal-border pl-8">
            <div className="text-xs text-terminal-muted uppercase tracking-wider">Available Cash</div>
            <div className="text-lg font-semibold text-terminal-text price-cell">
              ${cashBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          <div className="flex items-center gap-2 border-l border-terminal-border pl-8">
            <span className={`status-indicator ${
              connectionStatus.status === 'connected' ? 'status-connected' :
              connectionStatus.status === 'reconnecting' ? 'status-reconnecting' :
              'status-disconnected'
            }`}></span>
            <div className="text-xs text-terminal-muted">
              {connectionStatus.message}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
