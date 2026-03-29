import Navbar from './components/Navbar'
import Hero from './components/Hero'
import ImpactFindings from './components/ImpactFindings'
import FourDCostModel from './components/FourDCostModel'
import RouteProfilesTable from './components/RouteProfilesTable'

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 selection:bg-neon-cyan/30">
      <Navbar />
      <main>
        <Hero />
        <ImpactFindings />
        <FourDCostModel />
        <RouteProfilesTable />
      </main>
      
      <footer className="py-8 mt-24 border-t border-slate-800 text-center text-slate-500 text-sm">
        <p>LunarPath AI &copy; 2026 TUA Astro Hackathon</p>
      </footer>
    </div>
  )
}

export default App
