"use client";

import { useEffect, useState } from 'react';
import TradeTable from '@/components/TradeTable';

export default function TradesPage() {
  const [trades, setTrades] = useState<any[]>([]);

  useEffect(() => {
    // In a full implementation, you'd fetch from an Orchestrator Service
    // fetch('http://localhost:8082/api/v1/trades?limit=50').then(...)
    setTrades([
      { symbol: 'XAU/USD', type: 'BUY', entry_time: new Date().toISOString(), entry_price: 2680.50, exit_price: 2701.20, pl: +20.70, status: 'closed' },
      { symbol: 'XAU/USD', type: 'SELL', entry_time: new Date(Date.now() - 3600000).toISOString(), entry_price: 2690.00, exit_price: null, pl: -5.00, status: 'open' }
    ]);
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">Trade History</h1>
        <p className="text-gray-400">Paper-trading simulation P/L log</p>
      </header>
      
      <TradeTable trades={trades} />
    </div>
  );
}
