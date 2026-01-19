import React from 'react';
import { TopEventType } from '../types';

interface TopEventsTableProps {
  events: TopEventType[];
  totalByType: Record<string, number>;
}

const TopEventsTable: React.FC<TopEventsTableProps> = ({ events, totalByType }) => {
  // Merge real-time data with stats
  const mergedEvents = events.length > 0
    ? events
    : Object.entries(totalByType).map(([type, count]) => ({ type, count }));

  const total = mergedEvents.reduce((sum, e) => sum + e.count, 0);

  if (mergedEvents.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        No event data available
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-gray-400 text-sm">
            <th className="pb-3">Event Type</th>
            <th className="pb-3 text-right">Count</th>
            <th className="pb-3 text-right">Percentage</th>
            <th className="pb-3 w-32">Distribution</th>
          </tr>
        </thead>
        <tbody className="text-gray-300">
          {mergedEvents.slice(0, 7).map((event) => {
            const percentage = total > 0 ? (event.count / total) * 100 : 0;
            return (
              <tr key={event.type} className="border-t border-dashboard-border">
                <td className="py-3">
                  <EventBadge type={event.type} />
                </td>
                <td className="py-3 text-right font-mono">
                  {event.count.toLocaleString()}
                </td>
                <td className="py-3 text-right font-mono">
                  {percentage.toFixed(1)}%
                </td>
                <td className="py-3">
                  <div className="w-full bg-dashboard-bg rounded-full h-2">
                    <div
                      className="h-2 rounded-full bg-primary-500"
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

const EventBadge: React.FC<{ type: string }> = ({ type }) => {
  const colorMap: Record<string, string> = {
    user_action: 'bg-blue-900/50 text-blue-300',
    page_view: 'bg-green-900/50 text-green-300',
    click: 'bg-purple-900/50 text-purple-300',
    form_submit: 'bg-yellow-900/50 text-yellow-300',
    purchase: 'bg-emerald-900/50 text-emerald-300',
    error: 'bg-red-900/50 text-red-300',
    custom: 'bg-gray-900/50 text-gray-300',
  };

  const className = colorMap[type] || colorMap.custom;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${className}`}>
      {type.replace(/_/g, ' ')}
    </span>
  );
};

export default TopEventsTable;
