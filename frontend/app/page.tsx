"use client";

import { useState, useEffect } from 'react';
import PriceChart from '@/components/PriceChart';
import IndicatorChart from '@/components/IndicatorChart';
import SignalCard from '@/components/SignalCard';
import { Activity } from 'lucide-react';

export default function Dashboard() {
  const [livePrice, setLivePrice] = useState<number | null>(null);
  const [recentSignals, setRecentSignals] = useState<any[]>([]);
  const [liveAnalysis, setLiveAnalysis] = useState<any>(null);

  useEffect(() => {
    // Connect to WebSocket purely for live price ticker
    const priceWs = new WebSocket('ws://localhost:8081/ws/price');
    priceWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.price) setLivePrice(data.price);
      } catch (e) {}
    };

    // Connect to AI Analyzer WebSocket for live streaming Gemini Signals
    const analysisWs = new WebSocket('ws://localhost:8083/ws/analysis');
    analysisWs.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.analysis) {
          // Add it to the top of our feed
          const sig = {
            id: payload.timestamp,
            timestamp: payload.timestamp,
            type: payload.analysis.signal,
            confidence: payload.analysis.confidence || 0,
            ai_analysis: {
              trend: payload.analysis.trend,
              reasoning: payload.analysis.reasoning
            }
          };
          setLiveAnalysis(sig);
          setRecentSignals(prev => [sig, ...prev].slice(0, 10)); // Keep last 10
        }
      } catch(e) {}
    };

    // Fetch initial latest signals from REST
    fetch('http://localhost:8083/api/v1/signals?limit=3')
      .then(res => res.json())
      .then(data => {
        if (data.signals) setRecentSignals(data.signals);
      }).catch(console.error);

    return () => {
      priceWs.close();
      analysisWs.close();
    };
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
          {liveAnalysis && (
            <div className="bg-blue-900/20 border border-blue-800 p-4 rounded-xl flex items-start space-x-3 animate-fade-in">
              <div className="mt-1">
                <span className="flex h-3 w-3 rounded-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)] animate-pulse"></span>
              </div>
              <div>
                <h3 className="text-blue-400 font-semibold mb-1">Live Gemini Analysis ({liveAnalysis.type} - {liveAnalysis.confidence}%)</h3>
                <p className="text-gray-300 text-sm leading-relaxed">{liveAnalysis.ai_analysis.reasoning}</p>
              </div>
            </div>
          )}
          
          <PriceChart timeframe="M5" />
          <IndicatorChart timeframe="M5" />
        </div>
        
        {/* Sidebar Mini-feed */}
        <div className="xl:col-span-1 space-y-4">
          <div className="flex items-center space-x-2 mb-2">
            <Activity className="text-yellow-500" />
            <h2 className="text-lg font-bold">Latest AI Signals</h2>
          </div>
          
          <div className="space-y-4 max-h-[800px] overflow-y-auto pr-2">
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
