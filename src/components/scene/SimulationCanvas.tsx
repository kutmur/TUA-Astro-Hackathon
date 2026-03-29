import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { Suspense, useState, useEffect } from 'react'
import LunarTerrain from './LunarTerrain'
import Waypoints from './Waypoints'
import Routes from './Routes'
import { Card } from '../ui/card'

export default function SimulationCanvas() {
  const [stage, setStage] = useState(0)

  useEffect(() => {
    let active = true
    const sequence = async () => {
      await new Promise(r => setTimeout(r, 1000)); if(!active) return; setStage(1);
      await new Promise(r => setTimeout(r, 2000)); if(!active) return; setStage(2);
      await new Promise(r => setTimeout(r, 2500)); if(!active) return; setStage(3);
      await new Promise(r => setTimeout(r, 3000)); if(!active) return; setStage(4);
    }
    sequence()
    return () => { active = false }
  }, [])

  return (
    <>
      <Canvas camera={{ position: [40, 30, 40], fov: 45 }}>
        <color attach="background" args={['transparent']} />
        <ambientLight intensity={0.2} />
        <directionalLight position={[100, 100, 50]} intensity={1.5} color={'#ffffff'} />
        
        <Suspense fallback={null}>
          <LunarTerrain stage={stage} />
          <Waypoints stage={stage} />
          <Routes stage={stage} />
        </Suspense>

        <OrbitControls 
          enablePan={false}
          maxPolarAngle={Math.PI / 2.2}
          minDistance={20}
          maxDistance={120}
          autoRotate={stage === 1}
          autoRotateSpeed={0.5}
        />
      </Canvas>
      
      {/* UI Overlay Tools */}
      <div className="absolute bottom-4 left-4 bg-[#0a0a0a]/80 backdrop-blur border border-[#393939] p-3 rounded-lg text-xs font-mono space-y-1 z-10 pointer-events-none">
        <div className="text-(--mastra-text-secondary)">Simulation Status:</div>
        <div className="text-(--mastra-green-accent-2)">
          {stage === 0 && 'INITIALIZING SYS...'}
          {stage === 1 && 'DEM LOADED [HAWORTH]'}
          {stage === 2 && 'WAYPOINTS ACQUIRED'}
          {stage === 3 && 'COMPUTING ROUTES...'}
          {stage === 4 && 'PATH OPTIMIZED ✓'}
        </div>
      </div>
      
      {/* Floating Tooltips (HTML overlays over canvas) */}
      <div className={`absolute top-[20%] right-[15%] transition-opacity duration-1000 ${stage >= 4 ? 'opacity-100' : 'opacity-0'} pointer-events-none z-10`}>
        <Card className="bg-[rgba(2,6,23,0.8)] backdrop-blur-lg border border-neon-orange shadow-[0_0_15px_rgba(255,165,0,0.3)] p-3 min-w-[140px] rounded-lg">
          <div className="flex justify-between items-center gap-6 border-b border-[#393939] pb-2 mb-2">
            <span className="font-mono text-(--mastra-text-secondary) text-xs">Cost</span>
            <span className="font-bold text-(--mastra-text-primary) text-sm">590,502</span>
          </div>
          <span className="block text-[10px] text-neon-orange font-bold uppercase tracking-wider text-right">Optimal Path</span>
        </Card>
      </div>
    </>
  )
}
