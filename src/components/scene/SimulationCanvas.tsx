import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { Suspense, useState, useEffect } from 'react'
import LunarTerrain from './LunarTerrain'
import Waypoints from './Waypoints'
import Routes from './Routes'
import { useLanguage } from '../../context/LanguageContext'

export default function SimulationCanvas() {
  const [stage, setStage] = useState(0)
  const { t } = useLanguage()

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
          maxPolarAngle={Math.PI / 2.1}
          minDistance={20}
          maxDistance={120}
          autoRotate={stage === 1}
          autoRotateSpeed={0.5}
          enableDamping={true}
        />
      </Canvas>
      
      {/* UI Overlay Tools */}
      <div className="absolute bottom-4 left-4 bg-[rgba(10,10,10,0.8)] backdrop-blur border border-[#393939] p-3 rounded-lg text-xs font-mono space-y-1 z-10 pointer-events-none">
        <div className="text-(--mastra-text-secondary)">{t('simStatusLabel')}</div>
        <div className="text-(--mastra-green-accent-2)">
          {stage === 0 && t('simInit')}
          {stage === 1 && t('simLoaded')}
          {stage === 2 && t('simAcquired')}
          {stage === 3 && t('simComputing')}
          {stage === 4 && t('simOptimized')}
        </div>
      </div>
    </>
  )
}
