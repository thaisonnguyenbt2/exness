"use client";

import { useState, useEffect } from 'react';
import PriceChart from '@/components/PriceChart';
import IndicatorChart from '@/components/IndicatorChart';
import SignalCard from '@/components/SignalCard';
import { Activity } from 'lucide-react';

export default function Dashboard() {
  const [livePrice, setLivePrice] = useState<number | null>(null);
  const [recentSignals, setRecentSignals] = useState<any[]>([]);

  useEffect(() => {
    // Connect to WebSocket purely for live price ticker
    const ws = new WebSocket('ws://localhost:8080/ws/price');
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.price) setLivePrice(data.price);
      } catch (e) {}
    };

    // Fetch initial latest signals
    fetch('http://localhost:8081/api/v1/signals?limit=3')
      .then(res => res.json())
      .then(data => {
        if (data.signals) setRecentSignals(data.signals);
      }).catch(console.error);

    return () => ws.close();
  }, []);

  return (
    <div className="space-y-6">
      <header className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Market Dashboard</h1>
          <p className="text-gray-400 mt-1">Real-time analytical overview</p>
        </div>
        
        <div className="bg-gray-900 border border-gray-800 px-6 py-3 rounded-xl flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-400 uppercase font-semibold">Live Price</span>
          </div>
          <span className="text-2xl font-mono font-bold text-white">
            ${livePrice ? livePrice.toFixed(2) : '----.--'}
          </span>
        </div>
      </header>

      {/* Main Charting Section */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        <div className="xl:col-span-3 space-y-6">
          <PriceChart timeframe="M5" />
          <IndicatorChart timeframe="M5" />
        </div>
        
        {/* Sidebar Mini-feed */}
        <div className="xl:col-span-1 space-y-4">
          <div className="flex items-center space-x-2 mb-2">
            <Activity className="text-yellow-500" />
            <h2 className="text-lg font-bold">Latest AI Signals</h2>
          </div>
          
          <div className="space-y-4">
            {recentSignals.map(sig => (
               <SignalCard key={sig.id} signal={sig} />
            ))}
            {recentSignals.length === 0 && (
               <div className="text-center p-6 text-gray-500 border border-gray-800 border-dashed rounded-xl">
                 No signals generated yet.
               </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
