import React from 'react';
import { ConnectionStatus as ConnectionStatusType } from '../types';
import { useRealTimeMetrics } from '../hooks/useRealTimeMetrics';

const ConnectionStatus: React.FC = () => {
  const { connectionStatus } = useRealTimeMetrics();

  const statusConfig: Record<ConnectionStatusType, { label: string; className: string }> = {
    connected: {
      label: 'Live',
      className: 'connected',
    },
    disconnected: {
      label: 'Disconnected',
      className: 'disconnected',
    },
    connecting: {
      label: 'Connecting...',
      className: 'connecting',
    },
  };

  const config = statusConfig[connectionStatus];

  return (
    <div className={`connection-status ${config.className}`}>
      <span className="dot" />
      <span className="text-gray-300">{config.label}</span>
    </div>
  );
};

export default ConnectionStatus;
