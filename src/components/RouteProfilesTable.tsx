import { motion } from 'framer-motion'
import { Card } from './ui/card'

export default function RouteProfilesTable() {
  const profiles = [
    {
      name: "Optimal Path (Balanced 4D)",
      color: "bg-neon-orange",
      text: "text-neon-orange",
      weights: { d: 1.4, e: 4.0, s: 1.6, g: 0.22 },
      desc: "Optimal mission trade-off prioritizing safe traversal speeds."
    },
    {
      name: "Shortest Distance",
      color: "bg-neon-cyan",
      text: "text-neon-cyan",
      weights: { d: 9.5, e: 0.25, s: 0.05, g: 0.01 },
      desc: "Aggressive, high-speed profile ignoring severe inclines."
    },
    {
      name: "Thermal Safe",
      color: "bg-neon-magenta",
      text: "text-neon-magenta",
      weights: { d: 0.9, e: 1.2, s: 0.56, g: 6.5 },
      desc: "Strictly avoids shadows and high thermal cycling risks."
    }
  ]

  const maxVal = 10; 

  return (
    <section className="py-24 px-6 max-w-5xl mx-auto border-t border-(--border)/50">
      <div className="text-center mb-16">
        <h2 className="text-3xl font-bold mb-4 tracking-tight">Mission Profiles Config</h2>
        <p className="text-(--mastra-text-secondary)">Compare parameter weight distributions for adaptive planning.</p>
      </div>

      <div className="space-y-6">
        {profiles.map((p, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: i * 0.15 }}
            viewport={{ once: true }}
          >
            <Card className="flex flex-col md:flex-row gap-0 p-0 overflow-hidden bg-[rgba(255,255,255,0.02)] border-[0.5px] border-[#393939] items-stretch h-full">
              <div className="md:w-1/3 border-b md:border-b-0 md:border-r border-[#393939] p-6 bg-(--mastra-surface-2) flex flex-col justify-center">
                <h3 className={`text-sm tracking-wider uppercase font-bold mb-2 ${p.text}`}>{p.name}</h3>
                <p className="text-(--mastra-text-secondary) text-sm leading-relaxed">{p.desc}</p>
              </div>
              
              <div className="md:w-2/3 p-6 grid grid-cols-2 lg:grid-cols-4 gap-6 items-center">
                {Object.entries(p.weights).map(([key, val], idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex justify-between text-xs text-(--mastra-text-quaternary) uppercase font-mono">
                      <span>W_{key}</span>
                      <span className="text-(--mastra-text-primary)">{val.toFixed(2)}</span>
                    </div>
                    <div className="h-1.5 w-full bg-[#1e293b] rounded-full overflow-hidden border border-[#393939] relative">
                      <motion.div 
                        className={`absolute top-0 left-0 h-full ${p.color} shadow-[0_0_10px_currentColor]`}
                        initial={{ width: 0 }}
                        whileInView={{ width: `${(val / maxVal) * 100}%` }}
                        transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
                        viewport={{ once: true }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </section>
  )
}
