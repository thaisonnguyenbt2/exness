import { ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';

export default function SignalCard({ signal }: { signal: any }) {
  if (!signal) return null;
  
  const isBuy = signal.type === 'BUY';
  const Icon = isBuy ? ArrowUpRight : ArrowDownRight;
  const colorClass = isBuy ? 'text-green-500 bg-green-500/10' : 'text-red-500 bg-red-500/10';
  const borderClass = isBuy ? 'border-green-500/20' : 'border-red-500/20';

  const time = new Date(signal.timestamp).toLocaleTimeString();

  return (
    <div className={`p-4 rounded-xl border ${borderClass} bg-gray-900/50 flex flex-col space-y-3`}>
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-2">
           <div className={`p-2 rounded-lg ${colorClass}`}>
              <Icon size={20} />
           </div>
           <div>
              <p className="font-bold text-white leading-tight">{signal.type} {signal.symbol}</p>
              <p className="text-xs text-gray-400">{time} • {signal.timeframe}</p>
           </div>
        </div>
        <div className="text-right">
           <p className="font-bold text-white">{signal.confidence}%</p>
           <p className="text-xs text-gray-400">Confidence</p>
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-2 py-2 border-y border-gray-800">
         <div>
            <p className="text-xs text-gray-500">Entry</p>
            <p className="font-medium text-white">${signal.entry_price}</p>
         </div>
         <div>
            <p className="text-xs text-gray-500">Stop Loss</p>
            <p className="font-medium text-red-400">${signal.stop_loss}</p>
         </div>
         <div>
            <p className="text-xs text-gray-500">Take Profit</p>
            <p className="font-medium text-green-400">${signal.take_profit}</p>
         </div>
      </div>
      
      <div className="bg-gray-800/50 p-3 rounded-lg flex items-start space-x-2">
         <Activity className="text-blue-400 mt-1 flex-shrink-0" size={16} />
         <p className="text-sm text-gray-300 italic">{signal.ai_analysis?.reasoning}</p>
      </div>
    </div>
  );
}
