import React, { useState } from 'react';
import { api } from '../services/api';

const EventGenerator: React.FC = () => {
  const [count, setCount] = useState(100);
  const [eventType, setEventType] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const eventTypes = [
    { value: '', label: 'Random (all types)' },
    { value: 'user_action', label: 'User Action' },
    { value: 'page_view', label: 'Page View' },
    { value: 'click', label: 'Click' },
    { value: 'form_submit', label: 'Form Submit' },
    { value: 'purchase', label: 'Purchase' },
    { value: 'error', label: 'Error' },
    { value: 'custom', label: 'Custom' },
  ];

  const handleGenerate = async () => {
    setLoading(true);
    setResult(null);

    try {
      const response = await api.generateEvents({
        count,
        event_type: eventType || undefined,
      });
      setResult({
        success: true,
        message: `Generated ${response.generated} events`,
      });
    } catch (error) {
      setResult({
        success: false,
        message: 'Failed to generate events. Is the backend running?',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-gray-400 text-sm">
        Generate sample events for testing and demonstration purposes.
      </p>

      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Event Count</label>
          <input
            type="number"
            min="1"
            max="10000"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="w-32 bg-dashboard-bg border border-dashboard-border rounded-lg px-3 py-2 text-white focus:border-primary-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Event Type</label>
          <select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            className="w-48 bg-dashboard-bg border border-dashboard-border rounded-lg px-3 py-2 text-white focus:border-primary-500 focus:outline-none"
          >
            {eventTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-6 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-800 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors"
        >
          {loading ? 'Generating...' : 'Generate Events'}
        </button>
      </div>

      {result && (
        <div
          className={`p-3 rounded-lg text-sm ${
            result.success
              ? 'bg-green-900/20 text-green-400 border border-green-800'
              : 'bg-red-900/20 text-red-400 border border-red-800'
          }`}
        >
          {result.message}
        </div>
      )}
    </div>
  );
};

export default EventGenerator;
