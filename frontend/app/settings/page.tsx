"use client";

import { useState } from 'react';

export default function SettingsPage() {
  const [confidence, setConfidence] = useState(70);
  const [notify, setNotify] = useState(true);

  return (
    <div className="max-w-xl space-y-6">
      <header>
        <h1 className="text-3xl font-bold text-white mb-2">System Settings</h1>
        <p className="text-gray-400">Configure AI generation and notification rules</p>
      </header>
      
      <div className="bg-gray-900 border border-gray-800 p-6 rounded-xl space-y-6">
        <div>
           <label className="block text-sm font-medium text-gray-300 mb-2">
              Minimum AI Confidence Target (%)
           </label>
           <input 
              type="range" min="50" max="99" 
              value={confidence} 
              onChange={(e) => setConfidence(Number(e.target.value))}
              className="w-full accent-yellow-500" 
           />
           <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span>50%</span>
              <span className="font-bold text-white">{confidence}%</span>
              <span>99%</span>
           </div>
        </div>
        
        <div className="flex items-center space-x-3">
           <input 
             type="checkbox" 
             checked={notify} 
             onChange={(e) => setNotify(e.target.checked)}
             className="w-5 h-5 rounded border-gray-700 bg-gray-800 text-yellow-500 focus:ring-yellow-500"
           />
           <label className="text-sm font-medium text-gray-300">
              Enable Telegram Notifications
           </label>
        </div>
        
        <button className="w-full mt-4 bg-yellow-500 hover:bg-yellow-400 text-black font-bold py-2 px-4 rounded-lg transition-colors">
          Save Configuration
        </button>
      </div>
    </div>
  );
}
