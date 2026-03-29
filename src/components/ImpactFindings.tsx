import { motion } from 'framer-motion'
import { AlertTriangle, BatteryCharging, Network } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'

export default function ImpactFindings() {
  const { t } = useLanguage()

  const findings = [
    {
      icon: <AlertTriangle className="w-8 h-8 text-neon-magenta" />,
      title: t('impactRiskTitle'),
      desc: t('impactRiskDesc')
    },
    {
      icon: <BatteryCharging className="w-8 h-8 text-neon-green" />,
      title: t('impactEnergyTitle'),
      desc: t('impactEnergyDesc')
    },
    {
      icon: <Network className="w-8 h-8 text-neon-cyan" />,
      title: t('impactActionTitle'),
      desc: t('impactActionDesc')
    }
  ]

  return (
    <section className="py-24 px-6 max-w-7xl mx-auto border-t border-slate-800/50">
      <div className="text-center mb-16">
        <h2 className="text-3xl md:text-5xl font-bold mb-4 tracking-tight">{t('impactTitle')}</h2>
        <p className="text-slate-400 max-w-2xl mx-auto text-lg">
          {t('impactDesc')}
        </p>
      </div>
      
      <div className="grid md:grid-cols-3 gap-8">
        {findings.map((f, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: i * 0.15 }}
            viewport={{ once: true }}
            className="bg-slate-900 border border-slate-800 p-8 rounded-2xl hover:border-slate-700 transition-colors"
          >
            <div className="mb-4 bg-slate-950 p-3 rounded-lg inline-block border border-slate-800">
              {f.icon}
            </div>
            <h3 className="text-xl md:text-2xl font-semibold mb-3">{f.title}</h3>
            <p className="text-slate-400 leading-relaxed">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
