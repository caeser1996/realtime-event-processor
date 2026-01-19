import React from 'react';
import { RealTimeMetrics } from '../types';

interface MetricsGridProps {
  metrics: RealTimeMetrics | null;
}

const MetricsGrid: React.FC<MetricsGridProps> = ({ metrics }) => {
  const cards = [
    {
      label: 'Events/Second',
      value: metrics?.events_per_second?.toFixed(2) || '0.00',
      color: 'text-primary-400',
      icon: '⚡',
    },
    {
      label: 'Last Minute',
      value: metrics?.events_last_minute?.toLocaleString() || '0',
      color: 'text-green-400',
      icon: '📊',
    },
    {
      label: 'Last Hour',
      value: metrics?.events_last_hour?.toLocaleString() || '0',
      color: 'text-blue-400',
      icon: '📈',
    },
    {
      label: 'Active Users',
      value: metrics?.active_users?.toLocaleString() || '0',
      color: 'text-purple-400',
      icon: '👥',
    },
    {
      label: 'Active Sessions',
      value: metrics?.active_sessions?.toLocaleString() || '0',
      color: 'text-cyan-400',
      icon: '🔗',
    },
    {
      label: 'Errors (1h)',
      value: metrics?.error_count?.toLocaleString() || '0',
      color: metrics?.error_count && metrics.error_count > 0 ? 'text-red-400' : 'text-gray-400',
      icon: '⚠️',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {cards.map((card) => (
        <MetricCard key={card.label} {...card} />
      ))}
    </div>
  );
};

interface MetricCardProps {
  label: string;
  value: string;
  color: string;
  icon: string;
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value, color, icon }) => (
  <div className="card hover:border-primary-500/50 transition-colors">
    <div className="flex items-center justify-between mb-2">
      <span className="text-2xl">{icon}</span>
    </div>
    <div className={`stat-value ${color}`}>{value}</div>
    <div className="text-sm text-gray-400 mt-1">{label}</div>
  </div>
);

export default MetricsGrid;
