import Navbar from './components/Navbar'
import Hero from './components/Hero'
import ImpactFindings from './components/ImpactFindings'
import FourDCostModel from './components/FourDCostModel'
import RouteProfilesTable from './components/RouteProfilesTable'
import { LanguageProvider } from './context/LanguageContext'

function App() {
  return (
    <LanguageProvider>
      <div className="min-h-screen bg-[var(--ifm-background-color)] text-[var(--mastra-text-primary)] selection:bg-neon-cyan/30">
        <Navbar />
        <main>
          <Hero />
          <ImpactFindings />
          <FourDCostModel />
          <RouteProfilesTable />
        </main>
        
        <footer className="py-8 mt-24 border-t border-(--border)/50 text-center text-(--mastra-text-secondary) text-sm">
          <p>LunarPath AI &copy; 2026 TUA Astro Hackathon</p>
        </footer>
      </div>
    </LanguageProvider>
  )
}

export default App
