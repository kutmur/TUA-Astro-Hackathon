import { Terminal, Play } from 'lucide-react'
import { motion } from 'framer-motion'
import { useState } from 'react'
import SimulationCanvas from './scene/SimulationCanvas'
import { Button } from './ui/button'
import { useLanguage } from '../context/LanguageContext'

export default function Hero() {
  const { t } = useLanguage()
  const [simulationRunId, setSimulationRunId] = useState(0)

  const restartSimulation = () => {
    setSimulationRunId((prev) => prev + 1)
  }

  return (
    <section className="relative min-h-[90vh] flex items-center pt-20 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_50%,_rgba(0,255,255,0.05),_transparent_50%)] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.02)_1px,_transparent_1px)] [background-size:24px_24px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-6 w-full flex flex-col lg:flex-row items-center gap-12 z-10">
        
        <motion.div 
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="w-full lg:w-1/2 flex flex-col space-y-6"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 scale-90 sm:scale-100 origin-left border border-(--border) bg-(--mastra-surface-2)/50 rounded-full text-neon-cyan text-sm font-medium w-max backdrop-blur-sm">
            {t('heroTag')}
          </div>
          
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight text-(--mastra-text-primary) leading-[1.1]">
            {t('heroTitle')} <span className="text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan to-neon-green">{t('heroTitleHighlight')}</span>
          </h1>
          
          <p className="text-[var(--muted-foreground)] text-lg sm:text-xl max-w-xl leading-relaxed">
            {t('heroDesc')}
          </p>

          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <Button asChild variant="default" size="lg" className="w-full sm:w-auto font-semibold">
              <a href="https://github.com/kutmur/TUA-Astro-Hackathon" target="_blank" rel="noopener noreferrer">
                <Terminal className="w-5 h-5 mr-2" />
                {t('viewGithub')}
              </a>
            </Button>
            <Button
              variant="secondary"
              size="lg"
              onClick={restartSimulation}
              className="w-full sm:w-auto font-semibold relative overflow-hidden group border hover:border-(--mastra-green-accent-2)/50 hover:shadow-[0_0_20px_rgba(0,255,0,0.15)] transition-all"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-neon-cyan/[0.05] to-neon-green/[0.05] opacity-0 group-hover:opacity-100 transition-opacity" />
              <Play className="w-5 h-5 text-neon-cyan group-hover:text-(--mastra-green-accent-2) transition-colors mr-2" />
              {t('runSimulation')}
            </Button>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="w-full lg:w-1/2"
        >
          <div className="relative aspect-square sm:aspect-[4/3] w-full rounded-2xl border border-(--border)/50 bg-(--mastra-surface-2) shadow-[0_0_50px_rgba(0,255,255,0.05)] overflow-hidden cursor-move">
            <SimulationCanvas key={simulationRunId} />
          </div>
        </motion.div>

      </div>
    </section>
  )
}
