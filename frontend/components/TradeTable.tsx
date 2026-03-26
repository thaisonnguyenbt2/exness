export default function TradeTable({ trades }: { trades: any[] }) {
  if (!trades || trades.length === 0) {
    return (
      <div className="w-full text-center py-8 text-gray-500 border border-gray-800 rounded-xl bg-gray-900">
        No active or historical trades found.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border border-gray-800 rounded-xl bg-gray-900">
      <table className="w-full text-sm text-left text-gray-400">
        <thead className="text-xs text-gray-300 uppercase bg-gray-800/50 border-b border-gray-700">
          <tr>
            <th className="px-6 py-3">Time</th>
            <th className="px-6 py-3">Symbol</th>
            <th className="px-6 py-3">Type</th>
            <th className="px-6 py-3">Entry</th>
            <th className="px-6 py-3">Exit</th>
            <th className="px-6 py-3 text-right">P/L</th>
            <th className="px-6 py-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade, idx) => {
            const isProfit = trade.pl > 0;
            const plClass = isProfit ? 'text-green-500' : (trade.pl < 0 ? 'text-red-500' : '');
            
            return (
              <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/20">
                <td className="px-6 py-4">{new Date(trade.entry_time).toLocaleString()}</td>
                <td className="px-6 py-4 font-medium text-white">{trade.symbol}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded text-xs font-bold ${trade.type === 'BUY' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'}`}>
                    {trade.type}
                  </span>
                </td>
                <td className="px-6 py-4">${trade.entry_price}</td>
                <td className="px-6 py-4">{trade.exit_price ? `$${trade.exit_price}` : '-'}</td>
                <td className={`px-6 py-4 text-right font-bold ${plClass}`}>
                  {trade.pl ? `${isProfit ? '+' : ''}$${trade.pl}` : '-'}
                </td>
                <td className="px-6 py-4 text-gray-500">{trade.status}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
