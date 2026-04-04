import { motion } from 'framer-motion';
import { Heart, Rocket } from 'lucide-react';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import ImpactFindings from './components/ImpactFindings';
import FourDCostModel from './components/FourDCostModel';
import SimulationDashboard from './components/SimulationDashboard';
import MissionSpecialists from './components/MissionSpecialists';
import { LanguageProvider, useLanguage } from './context/LanguageContext';

// ============================================================================
// ENHANCED FOOTER
// ============================================================================

function Footer() {
  const { t } = useLanguage();
  const currentYear = new Date().getFullYear();

  return (
    <footer className="relative py-12 mt-24 border-t border-[#393939]/50 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-t from-[rgba(0,255,255,0.02)] to-transparent pointer-events-none" />
      
      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Main footer content */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Logo and tagline */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="flex items-center gap-3"
          >
            <div className="p-2 rounded-lg bg-gradient-to-br from-[#00ffff]/20 to-[#ffa500]/20 border border-[#393939]">
              <Rocket className="w-5 h-5 text-[#00ffff]" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-wide text-white">ThresholdAI</span>
              <p className="text-xs text-[#64748b]">TUA Astro Hackathon 2026</p>
            </div>
          </motion.div>

          {/* Center - Made with love */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            viewport={{ once: true }}
            className="flex items-center gap-2 text-sm text-[#cbd5e1]"
          >
            <span>{t('madeWith')}</span>
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <Heart className="w-4 h-4 text-[#ff00ff] fill-[#ff00ff]" />
            </motion.div>
            <span>{t('forTheFuture')}</span>
          </motion.div>

          {/* Right - Copyright */}
          <motion.p
            initial={{ opacity: 0, y: 10 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            viewport={{ once: true }}
            className="text-sm text-[#64748b]"
          >
            &copy; {currentYear} ThresholdAI
          </motion.p>
        </div>

        {/* Bottom tech badges */}
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          viewport={{ once: true }}
          className="mt-8 pt-6 border-t border-[#393939]/50 flex flex-wrap justify-center gap-3"
        >
          {['React', 'TypeScript', 'Vite', 'Tailwind CSS', 'Three.js', 'Framer Motion'].map((tech) => (
            <span 
              key={tech}
              className="text-[10px] font-mono px-2 py-1 rounded bg-[rgba(255,255,255,0.02)] border border-[#393939]/50 text-[#64748b] hover:text-[#cbd5e1] transition-colors"
            >
              {tech}
            </span>
          ))}
        </motion.div>
      </div>

      {/* Decorative corner elements */}
      <div className="absolute bottom-4 left-4 w-8 h-8 border-b border-l border-[#393939]/30" />
      <div className="absolute bottom-4 right-4 w-8 h-8 border-b border-r border-[#393939]/30" />
    </footer>
  );
}

// ============================================================================
// SECTION DIVIDER
// ============================================================================

function SectionDivider() {
  return (
    <motion.div
      initial={{ scaleX: 0 }}
      whileInView={{ scaleX: 1 }}
      transition={{ duration: 1 }}
      viewport={{ once: true }}
      className="max-w-7xl mx-auto px-6"
    >
      <div className="h-px bg-gradient-to-r from-transparent via-[#393939] to-transparent" />
    </motion.div>
  );
}

// ============================================================================
// APP CONTENT
// ============================================================================

function AppContent() {
  return (
    <div className="min-h-screen bg-[#020617] text-[#f8fafc] selection:bg-[#00ffff]/30">
      {/* Ambient background effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#00ffff]/[0.03] rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-[#ffa500]/[0.03] rounded-full blur-[100px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#ff00ff]/[0.02] rounded-full blur-[150px]" />
      </div>

      {/* Navigation */}
      <Navbar />
      
      {/* Main Content */}
      <main className="relative z-10">
        {/* Hero Section - Original 3D Canvas */}
        <Hero />
        
        {/* Impact Findings */}
        <ImpactFindings />
        
        <SectionDivider />
        
        {/* 4D Cost Model Explanation */}
        <FourDCostModel />
        
        <SectionDivider />
        
        {/* NEW: Interactive Mission Control Dashboard */}
        <SimulationDashboard />
        
        <SectionDivider />
        
        {/* NEW: Team Section */}
        <MissionSpecialists />
      </main>
      
      {/* Enhanced Footer */}
      <Footer />
    </div>
  );
}

// ============================================================================
// MAIN APP - Wrapped with Providers
// ============================================================================

function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
}

export default App;
