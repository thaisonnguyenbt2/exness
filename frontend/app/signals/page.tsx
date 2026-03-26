"use client";

import { useEffect, useState } from 'react';
import SignalCard from '@/components/SignalCard';

export default function SignalsPage() {
  const [signals, setSignals] = useState<any[]>([]);

  useEffect(() => {
    fetch('http://localhost:8081/api/v1/signals?limit=50')
      .then(res => res.json())
      .then(data => {
        if (data.signals) setSignals(data.signals);
      }).catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">Signal History</h1>
        <p className="text-gray-400">Historical AI-generated trading recommendations</p>
      </header>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {signals.map(s => <SignalCard key={s.id} signal={s} />)}
        {signals.length === 0 && (
          <div className="col-span-full py-12 text-center text-gray-500 border border-gray-800 rounded-xl">
             No historical signals found in MongoDB.
          </div>
        )}
      </div>
    </div>
  );
}
