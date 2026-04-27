import { useEffect, useRef, useState } from 'react';
import { PriceUpdate, ConnectionStatus } from '../types';

export function useSSE() {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    status: 'disconnected',
    message: 'Connecting...',
  });
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const connect = () => {
      try {
        const eventSource = new EventSource('/api/stream/prices');
        eventSourceRef.current = eventSource;

        eventSource.addEventListener('message', (event) => {
          try {
            const data = JSON.parse(event.data) as PriceUpdate;
            setPrices((prev) => ({
              ...prev,
              [data.ticker]: data,
            }));
            setConnectionStatus({
              status: 'connected',
              message: 'Connected',
            });
          } catch (err) {
            console.error('Failed to parse price update:', err);
          }
        });

        eventSource.addEventListener('error', () => {
          eventSource.close();
          setConnectionStatus({
            status: 'disconnected',
            message: 'Connection lost',
          });

          reconnectTimeoutRef.current = setTimeout(() => {
            setConnectionStatus({
              status: 'reconnecting',
              message: 'Reconnecting...',
            });
            connect();
          }, 3000);
        });

        eventSource.addEventListener('open', () => {
          setConnectionStatus({
            status: 'connected',
            message: 'Connected',
          });
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
        });
      } catch (err) {
        console.error('Failed to establish SSE connection:', err);
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      }
    };

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, []);

  return { prices, connectionStatus };
}
