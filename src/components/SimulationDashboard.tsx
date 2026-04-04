import { motion } from 'framer-motion';
import { Activity, Gauge, Cpu } from 'lucide-react';
import { MissionProvider, useMission } from '../context/MissionContext';
import { useLanguage } from '../context/LanguageContext';
import InteractiveMissionWeights from './InteractiveMissionWeights';
import SimulationVisualizer from './SimulationVisualizer';

// ============================================================================
// LIVE METRICS PANEL
// ============================================================================

function LiveMetricsPanel() {
  const { weights, activeProfileId } = useMission();
  
  // Calculate real-time metrics based on weights
  const riskScore = Math.round(100 - (weights.slope * 5 + weights.shadow * 10));
  const energyEfficiency = Math.round(100 - weights.slope * 8);
  
  const metrics = [
    { 
      label: 'Risk Score', 
      value: `${Math.max(0, Math.min(100, riskScore))}%`,
      icon: Activity,
      color: riskScore > 70 ? 'text-neon-green' : riskScore > 40 ? 'text-neon-orange' : 'text-neon-magenta',
      bgColor: riskScore > 70 ? 'bg-neon-green/10' : riskScore > 40 ? 'bg-neon-orange/10' : 'bg-neon-magenta/10',
    },
    { 
      label: 'Energy Eff.', 
      value: `${Math.max(0, Math.min(100, energyEfficiency))}%`,
      icon: Gauge,
      color: energyEfficiency > 60 ? 'text-neon-cyan' : 'text-neon-orange',
      bgColor: energyEfficiency > 60 ? 'bg-neon-cyan/10' : 'bg-neon-orange/10',
    },
    { 
      label: 'Profile', 
      value: activeProfileId.toUpperCase(),
      icon: Cpu,
      color: 'text-neon-cyan',
      bgColor: 'bg-neon-cyan/10',
    },
  ];

  return (
    <div className="grid grid-cols-3 gap-3 mb-6">
      {metrics.map((metric, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.1 }}
          className={`${metric.bgColor} backdrop-blur-sm border border-[#393939] rounded-lg p-3 text-center`}
        >
          <metric.icon className={`w-4 h-4 ${metric.color} mx-auto mb-1`} />
          <p className="text-[10px] text-[#64748b] uppercase tracking-wider">{metric.label}</p>
          <motion.p 
            className={`text-sm font-mono font-bold ${metric.color}`}
            key={metric.value}
            initial={{ scale: 1.1 }}
            animate={{ scale: 1 }}
          >
            {metric.value}
          </motion.p>
        </motion.div>
      ))}
    </div>
  );
}

// ============================================================================
// DASHBOARD INNER CONTENT (needs MissionProvider context)
// ============================================================================

function DashboardContent() {
  const { t } = useLanguage();

  return (
    <section className="py-24 px-6 max-w-7xl mx-auto" id="dashboard">
      {/* Section Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        viewport={{ once: true }}
        className="text-center mb-12"
      >
        <motion.div
          initial={{ scale: 0 }}
          whileInView={{ scale: 1 }}
          transition={{ type: 'spring', delay: 0.2 }}
          viewport={{ once: true }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-6 rounded-full bg-gradient-to-r from-[#00ffff]/10 to-[#ffa500]/10 border border-[#393939]"
        >
          <div className="w-2 h-2 rounded-full bg-[#00ff00] animate-pulse" />
          <span className="text-sm font-mono text-[#00ffff]">LIVE SYSTEM</span>
        </motion.div>
        
        <h2 className="text-3xl md:text-5xl font-bold mb-4 tracking-tight text-[#f8fafc]">
          {t('dashboardTitle')}
        </h2>
        <p className="text-[#cbd5e1] max-w-2xl mx-auto">
          {t('dashboardDesc')}
        </p>
      </motion.div>

      {/* Main Dashboard Grid */}
      <div className="grid lg:grid-cols-2 gap-8">
        {/* Left Column - Controls */}
        <motion.div
          initial={{ opacity: 0, x: -30 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="space-y-6"
        >
          <LiveMetricsPanel />
          <InteractiveMissionWeights />
        </motion.div>

        {/* Right Column - Visualizer */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          whileInView={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          viewport={{ once: true }}
        >
          <SimulationVisualizer />
        </motion.div>
      </div>

      {/* Bottom Decorative Elements */}
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 1, delay: 0.5 }}
        viewport={{ once: true }}
        className="mt-16 relative"
      >
        {/* Connecting data flow lines */}
        <svg className="w-full h-8 opacity-30" viewBox="0 0 1000 30">
          <defs>
            <linearGradient id="dataFlow" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#00ffff" stopOpacity="0" />
              <stop offset="50%" stopColor="#00ffff" stopOpacity="1" />
              <stop offset="100%" stopColor="#00ffff" stopOpacity="0" />
            </linearGradient>
          </defs>
          <motion.line
            x1="0"
            y1="15"
            x2="1000"
            y2="15"
            stroke="url(#dataFlow)"
            strokeWidth="1"
            strokeDasharray="5,10"
            initial={{ pathLength: 0 }}
            whileInView={{ pathLength: 1 }}
            transition={{ duration: 2 }}
            viewport={{ once: true }}
          />
        </svg>
        
        {/* Tech stack badges */}
        <div className="flex justify-center gap-4 mt-4">
          {['A* Algorithm', 'Real DEM', '4D Cost Model', 'Multi-Objective'].map((tech, i) => (
            <motion.span
              key={tech}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i }}
              viewport={{ once: true }}
              className="text-[10px] font-mono px-3 py-1 rounded-full bg-[rgba(255,255,255,0.03)] border border-[#393939] text-[#64748b]"
            >
              {tech}
            </motion.span>
          ))}
        </div>
      </motion.div>
    </section>
  );
}

// ============================================================================
// MAIN EXPORT - Wraps content with MissionProvider
// ============================================================================

export default function SimulationDashboard() {
  return (
    <MissionProvider>
      <DashboardContent />
    </MissionProvider>
  );
}
