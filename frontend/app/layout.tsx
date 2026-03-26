import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import Link from 'next/link'
import { LayoutDashboard, Activity, ListOrdered, Settings } from 'lucide-react'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'XAU/USD Trading Platform',
  description: 'AI-Powered Gold Trading Analysis',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-black text-gray-100 min-h-screen flex`}>
        {/* Sidebar */}
        <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col hidden md:flex">
          <div className="p-6">
            <h1 className="text-xl font-bold bg-gradient-to-r from-yellow-500 to-yellow-200 bg-clip-text text-transparent">
               GOLD AI PLATFORM
            </h1>
          </div>
          <nav className="flex-1 px-4 space-y-2 mt-4">
            <Link href="/" className="flex items-center space-x-3 px-4 py-3 rounded-xl hover:bg-gray-800 transition-colors">
              <LayoutDashboard size={20} className="text-gray-400" />
              <span>Dashboard</span>
            </Link>
            <Link href="/signals" className="flex items-center space-x-3 px-4 py-3 rounded-xl hover:bg-gray-800 transition-colors">
              <Activity size={20} className="text-gray-400" />
              <span>AI Signals</span>
            </Link>
            <Link href="/trades" className="flex items-center space-x-3 px-4 py-3 rounded-xl hover:bg-gray-800 transition-colors">
              <ListOrdered size={20} className="text-gray-400" />
              <span>Trade Log</span>
            </Link>
            <Link href="/settings" className="flex items-center space-x-3 px-4 py-3 rounded-xl hover:bg-gray-800 transition-colors">
              <Settings size={20} className="text-gray-400" />
              <span>System Settings</span>
            </Link>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8">
           {children}
        </main>
      </body>
    </html>
  )
}
