import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { TimeSeriesData } from '../types';
import { format } from 'date-fns';

interface EventChartProps {
  data: TimeSeriesData[];
}

const EventChart: React.FC<EventChartProps> = ({ data }) => {
  const formattedData = data.map((item) => ({
    ...item,
    time: format(new Date(item.timestamp), 'HH:mm'),
  }));

  if (data.length === 0) {
    return (
      <div className="chart-container flex items-center justify-center text-gray-400">
        No data available
      </div>
    );
  }

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="time"
            stroke="#94a3b8"
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            stroke="#94a3b8"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#f8fafc' }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="event_count"
            name="Events"
            stroke="#0ea5e9"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="unique_users"
            name="Unique Users"
            stroke="#8b5cf6"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EventChart;
