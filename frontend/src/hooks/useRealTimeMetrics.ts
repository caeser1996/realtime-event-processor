import { useState, useEffect, useCallback } from 'react';
import { RealTimeMetrics, ConnectionStatus } from '../types';
import { wsService } from '../services/websocket';
import { api } from '../services/api';

interface UseRealTimeMetricsResult {
  metrics: RealTimeMetrics | null;
  connectionStatus: ConnectionStatus;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useRealTimeMetrics(): UseRealTimeMetricsResult {
  const [metrics, setMetrics] = useState<RealTimeMetrics | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.getRealTimeMetrics();
      setMetrics(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch metrics');
      console.error('Error fetching metrics:', err);
    }
  }, []);

  useEffect(() => {
    // Subscribe to WebSocket updates
    const unsubscribeMetrics = wsService.onMetrics((newMetrics) => {
      setMetrics(newMetrics);
      setError(null);
    });

    const unsubscribeStatus = wsService.onStatusChange((status) => {
      setConnectionStatus(status);
    });

    // Connect to WebSocket
    wsService.connect();

    // Initial fetch as fallback
    refresh();

    // Cleanup
    return () => {
      unsubscribeMetrics();
      unsubscribeStatus();
    };
  }, [refresh]);

  // Fallback polling when WebSocket is disconnected
  useEffect(() => {
    if (connectionStatus === 'disconnected') {
      const interval = setInterval(refresh, 10000);
      return () => clearInterval(interval);
    }
  }, [connectionStatus, refresh]);

  return { metrics, connectionStatus, error, refresh };
}
