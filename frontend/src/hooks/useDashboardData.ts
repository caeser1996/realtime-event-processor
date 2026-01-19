import { useState, useEffect, useCallback } from 'react';
import { DashboardData, TimeSeriesData, EventStats } from '../types';
import { api } from '../services/api';

interface UseDashboardDataResult {
  data: DashboardData | null;
  timeSeries: TimeSeriesData[];
  stats: EventStats | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useDashboardData(): UseDashboardDataResult {
  const [data, setData] = useState<DashboardData | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesData[]>([]);
  const [stats, setStats] = useState<EventStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const dashboardData = await api.getDashboard();
      setData(dashboardData);
      setTimeSeries(dashboardData.timeseries?.data || []);
      setStats(dashboardData.stats);
      setError(null);
    } catch (err) {
      setError('Failed to fetch dashboard data');
      console.error('Error fetching dashboard data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();

    // Refresh every 30 seconds
    const interval = setInterval(refresh, 30000);

    return () => clearInterval(interval);
  }, [refresh]);

  return { data, timeSeries, stats, loading, error, refresh };
}
