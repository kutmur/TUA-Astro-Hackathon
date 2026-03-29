import { motion } from 'framer-motion'
import { Card, CardHeader, CardTitle, CardContent } from './ui/card'
import { useLanguage } from '../context/LanguageContext'

export default function FourDCostModel() {
  const { t } = useLanguage()

  const variables = [
    {
      letter: "D",
      name: t('varDName'),
      desc: t('varDDesc'),
      glow: "hover:shadow-[0_0_25px_rgba(0,255,255,0.1)] hover:border-neon-cyan/40 hover:bg-(--mastra-surface-3)"
    },
    {
      letter: "E",
      name: t('varEName'),
      desc: t('varEDesc'),
      glow: "hover:shadow-[0_0_25px_rgba(255,165,0,0.1)] hover:border-neon-orange/40 hover:bg-(--mastra-surface-3)"
    },
    {
      letter: "S",
      name: t('varSName'),
      desc: t('varSDesc'),
      glow: "hover:shadow-[0_0_25px_rgba(255,0,255,0.1)] hover:border-neon-magenta/40 hover:bg-(--mastra-surface-3)"
    },
    {
      letter: "G",
      name: t('varGName'),
      desc: t('varGDesc'),
      glow: "hover:shadow-[0_0_25px_rgba(0,255,0,0.1)] hover:border-(--mastra-green-accent-2)/40 hover:bg-(--mastra-surface-3)"
    }
  ]

  return (
    <section className="py-24 px-6 max-w-7xl mx-auto">
      <div className="text-center mb-16">
        <h2 className="text-3xl md:text-5xl font-bold mb-4 tracking-tight">{t('costModelTitle')}</h2>
        <p className="text-(--mastra-text-secondary)">{t('costModelDesc')}</p>
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        whileInView={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
        className="mb-12 flex justify-center"
      >
        <Card className="p-6 md:p-10 shadow-2xl bg-(--mastra-surface-2) border-[0.5px] border-[#393939]">
          <code className="text-[10px] sm:text-lg md:text-2xl font-mono text-center text-(--mastra-text-primary)">
            C<sub className="text-sm">total</sub> = [ (W<sub className="text-sm">d</sub> * <span className="text-neon-cyan">D</span>) + (W<sub className="text-sm">e</sub> * <span className="text-neon-orange">E</span>) + (W<sub className="text-sm">s</sub> * <span className="text-neon-magenta">S</span>) + (W<sub className="text-sm">g</sub> * <span className="text-(--mastra-green-accent-2)">G</span>) ] * 1000
          </code>
        </Card>
      </motion.div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6">
        {variables.map((v, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
            viewport={{ once: true }}
            className="h-full"
          >
            <Card className={`h-full transition-all duration-300 bg-[rgba(255,255,255,0.02)] border-[0.5px] border-[#393939] ${v.glow}`}>
              <CardHeader className="pb-2">
                <div className="text-4xl md:text-5xl font-bold opacity-20 mb-2">{v.letter}</div>
                <CardTitle className="text-lg md:text-xl text-(--mastra-text-primary)">{v.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-(--mastra-text-secondary) text-xs md:text-sm">{v.desc}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
