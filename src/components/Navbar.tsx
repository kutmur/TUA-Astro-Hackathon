import { Terminal } from 'lucide-react'
import { Button } from './ui/button'
import { useLanguage } from '../context/LanguageContext'

export default function Navbar() {
  const { language, setLanguage, t } = useLanguage()

  const toggleLang = () => {
    setLanguage(language === 'tr' ? 'en' : 'tr')
  }

  return (
    <nav className="fixed top-0 left-0 w-full z-50 border-b border-(--border)/60 bg-[var(--ifm-background-color)]/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src={`${import.meta.env.BASE_URL}logo.png`} alt="ThresholdAI Logo" className="h-8 w-auto" />
          <span className="font-bold text-lg tracking-wide text-white">ThresholdAI</span>
        </div>
        
        <div className="flex items-center gap-4">
          <button 
            onClick={toggleLang}
            className="text-xs font-mono font-bold tracking-wider px-2 py-1 rounded bg-(--mastra-surface-2) border border-[#393939] hover:bg-(--mastra-surface-3) transition-colors text-(--mastra-text-secondary) hover:text-(--mastra-text-primary)"
          >
            {language === 'tr' ? 'TR | en' : 'tr | EN'}
          </button>
          
          <a href="https://github.com" target="_blank" rel="noreferrer">
             <Button variant="outline" className="border-(--border) hover:border-(--mastra-green-accent-2)/50 transition-all">
               <Terminal className="w-4 h-4 mr-2" />
               {t('viewGithub')}
             </Button>
          </a>
        </div>
      </div>
    </nav>
  )
}
