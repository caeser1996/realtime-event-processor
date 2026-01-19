import React from 'react';
import ConnectionStatus from './ConnectionStatus';

const Header: React.FC = () => {
  return (
    <header className="bg-dashboard-card border-b border-dashboard-border">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-white">
              Event Processor Dashboard
            </h1>
            <span className="text-sm text-gray-400">Real-time Analytics</span>
          </div>
          <div className="flex items-center gap-6">
            <ConnectionStatus />
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
            >
              API Docs
            </a>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
