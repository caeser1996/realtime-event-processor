import React from 'react';

const LoadingSpinner: React.FC = () => {
  return (
    <div className="flex flex-col items-center gap-4">
      <div className="spinner" />
      <span className="text-gray-400">Loading dashboard...</span>
    </div>
  );
};

export default LoadingSpinner;
