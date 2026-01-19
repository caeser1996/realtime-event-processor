import React from 'react';
import { useRealTimeMetrics } from '../hooks/useRealTimeMetrics';
import { useDashboardData } from '../hooks/useDashboardData';
import MetricsGrid from './MetricsGrid';
import EventChart from './EventChart';
import TopEventsTable from './TopEventsTable';
import EventGenerator from './EventGenerator';
import LoadingSpinner from './LoadingSpinner';

const Dashboard: React.FC = () => {
  const { metrics, error: metricsError } = useRealTimeMetrics();
  const { timeSeries, stats, loading, error: dataError } = useDashboardData();

  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner />
      </div>
    );
  }

  const error = metricsError || dataError;

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Real-time Metrics */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="live-indicator pl-4">Real-time Metrics</span>
        </h2>
        <MetricsGrid metrics={metrics} />
      </section>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="card">
          <h3 className="text-md font-semibold text-white mb-4">
            Events Over Time
          </h3>
          <EventChart data={timeSeries} />
        </section>

        <section className="card">
          <h3 className="text-md font-semibold text-white mb-4">
            Top Event Types
          </h3>
          <TopEventsTable
            events={metrics?.top_event_types || []}
            totalByType={stats?.events_by_type || {}}
          />
        </section>
      </div>

      {/* Event Generator */}
      <section className="card">
        <h3 className="text-md font-semibold text-white mb-4">
          Event Generator
        </h3>
        <EventGenerator />
      </section>

      {/* Stats Summary */}
      {stats && (
        <section className="card">
          <h3 className="text-md font-semibold text-white mb-4">
            24-Hour Summary
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatItem label="Total Events" value={stats.total_events.toLocaleString()} />
            <StatItem label="Unique Users" value={stats.unique_users.toLocaleString()} />
            <StatItem label="Unique Sessions" value={stats.unique_sessions.toLocaleString()} />
            <StatItem
              label="Event Types"
              value={Object.keys(stats.events_by_type).length.toString()}
            />
          </div>
        </section>
      )}
    </div>
  );
};

const StatItem: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="text-center p-4 bg-dashboard-bg rounded-lg">
    <div className="text-2xl font-bold text-white">{value}</div>
    <div className="text-sm text-gray-400">{label}</div>
  </div>
);

export default Dashboard;
