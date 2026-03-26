"use client";

import React, { useEffect, useState } from 'react';
import {
  ComposedChart,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Bar,
  Line,
  CartesianGrid,
  ReferenceLine
} from 'recharts';

export default function IndicatorChart({ timeframe = 'M5' }) {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    // Initial fetch
    const fetchCandles = async () => {
      try {
        const res = await fetch(`http://localhost:8080/api/v1/candles?timeframe=${timeframe}&limit=100`);
        const json = await res.json();
        if (json.candles) {
          const formatted = json.candles.map((c: any) => ({
             ...c.indicators,
             time: new Date(c.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
             // MACD destructuring for easy charting
             macdVal: c.indicators?.macd?.value,
             macdSig: c.indicators?.macd?.signal,
             macdHist: c.indicators?.macd?.histogram
          }));
          setData(formatted);
        }
      } catch (err) {
        console.error("Failed to fetch candles", err);
      }
    };
    fetchCandles();
  }, [timeframe]);

  if (data.length === 0) return null;

  return (
    <div className="w-full flex space-x-4">
      {/* RSI Panel */}
      <div className="flex-1 h-64 bg-gray-900 p-4 rounded-xl border border-gray-800">
        <h3 className="text-sm font-bold mb-2 text-gray-400">RSI (14)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis domain={[0, 100]} stroke="#9ca3af" width={40} orientation="right" />
            <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" />
            <ReferenceLine y={30} stroke="#22c55e" strokeDasharray="3 3" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', color: '#fff'}} />
            <Line type="monotone" dataKey="rsi" stroke="#a855f7" dot={false} strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      
      {/* MACD Panel */}
      <div className="flex-1 h-64 bg-gray-900 p-4 rounded-xl border border-gray-800">
        <h3 className="text-sm font-bold mb-2 text-gray-400">MACD (12, 26, 9)</h3>
        <ResponsiveContainer width="100%" height="90%">
          <ComposedChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
            <XAxis dataKey="time" hide />
            <YAxis stroke="#9ca3af" width={40} orientation="right" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', color: '#fff'}} />
            <Bar dataKey="macdHist" fill="#6b7280" />
            <Line type="monotone" dataKey="macdVal" stroke="#3b82f6" dot={false} strokeWidth={2} />
            <Line type="monotone" dataKey="macdSig" stroke="#f59e0b" dot={false} strokeWidth={2} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
