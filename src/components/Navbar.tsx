import { Terminal } from 'lucide-react'
import { Button } from './ui/button'

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 w-full z-50 border-b border-(--border)/60 bg-[var(--ifm-background-color)]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-gradient-to-tr from-neon-cyan to-neon-green" />
          <span className="font-bold text-lg tracking-wide text-white">LunarPath AI</span>
        </div>
        
        <div className="flex items-center gap-6">
          <a href="https://github.com" target="_blank" rel="noreferrer">
             <Button variant="outline" className="border-(--border) hover:border-(--mastra-green-accent-2)/50 transition-all">
               <Terminal className="w-4 h-4" />
               View GitHub
             </Button>
          </a>
        </div>
      </div>
    </nav>
  )
}
