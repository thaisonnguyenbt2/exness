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
  CartesianGrid
} from 'recharts';

/**
 * Custom Candlestick shape for Recharts
 */
const CandlestickShape = (props: any) => {
  const { x, y, width, height, payload } = props;
  const isGrowing = payload.close > payload.open;
  const color = isGrowing ? '#22c55e' : '#ef4444'; 
  const wickTop = Math.min(payload.open, payload.close);
  const wickBottom = Math.max(payload.open, payload.close);
  
  // Calculate relative positions for the wick
  // Note: Y-axis is inverted in SVGs (0 is top)
  const openY = props.yAxis.scale(payload.open);
  const closeY = props.yAxis.scale(payload.close);
  const highY = props.yAxis.scale(payload.high);
  const lowY = props.yAxis.scale(payload.low);

  const boxTop = Math.min(openY, closeY);
  const boxHeight = Math.abs(openY - closeY) || 1; 

  const halfWidth = width / 2;

  return (
    <g stroke={color} fill={color} strokeWidth={2}>
      {/* High-Low Wick */}
      <line 
        x1={x + halfWidth} 
        y1={highY} 
        x2={x + halfWidth} 
        y2={lowY} 
      />
      {/* Open-Close Body */}
      <rect 
        x={x} 
        y={boxTop} 
        width={width} 
        height={boxHeight} 
      />
    </g>
  );
};

export default function PriceChart({ timeframe = 'M5' }) {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    // Initial fetch
    const fetchCandles = async () => {
      try {
        const res = await fetch(`http://localhost:8080/api/v1/candles?timeframe=${timeframe}&limit=100`);
        const json = await res.json();
        if (json.candles) {
          // Format timestamps
          const formatted = json.candles.map((c: any) => ({
             ...c,
             time: new Date(c.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
             // For the composed chart generic data
             range: [c.low, c.high]
          }));
          setData(formatted);
        }
      } catch (err) {
        console.error("Failed to fetch candles", err);
      }
    };
    fetchCandles();
  }, [timeframe]);

  if (data.length === 0) return <div className="h-96 flex items-center justify-center border border-gray-800 rounded-xl bg-gray-900 text-gray-500">Loading Market Data...</div>;

  // Calculate dynamic domain
  const min = Math.min(...data.map(d => d.low)) * 0.9995;
  const max = Math.max(...data.map(d => d.high)) * 1.0005;

  return (
    <div className="w-full h-96 bg-gray-900 p-4 rounded-xl border border-gray-800">
      <h2 className="text-xl font-bold mb-4 text-white">XAU/USD ({timeframe})</h2>
      <ResponsiveContainer width="100%" height="90%">
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
          <XAxis dataKey="time" stroke="#9ca3af" tick={{fill: '#9ca3af'}} />
          <YAxis domain={[min, max]} stroke="#9ca3af" tick={{fill: '#9ca3af'}} width={80} orientation="right" />
          <Tooltip 
             contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#fff' }}
             itemStyle={{ color: '#fff' }}
          />
          {/* We use Bar as a proxy to render our custom candlestick shape */}
          <Bar dataKey="range" shape={<CandlestickShape />} isAnimationActive={false} />
          {/* Overlay EMAs */}
          <Line type="monotone" dataKey="indicators.ema_9" stroke="#3b82f6" dot={false} strokeWidth={2} name="EMA 9" />
          <Line type="monotone" dataKey="indicators.ema_21" stroke="#f59e0b" dot={false} strokeWidth={2} name="EMA 21" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
