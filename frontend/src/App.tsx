import React from 'react';
import Dashboard from './components/Dashboard';
import Header from './components/Header';

function App() {
  return (
    <div className="min-h-screen bg-dashboard-bg">
      <Header />
      <main className="container mx-auto px-4 py-6">
        <Dashboard />
      </main>
    </div>
  );
}

export default App;
