import { useMemo } from 'react'
import * as THREE from 'three'
import { Line, Html } from '@react-three/drei'
import { getHeight } from '../../lib/terrainMath'
import { useLanguage } from '../../context/LanguageContext'
import { Card } from '../ui/card'

function RouteTooltip({ name, cost, colorClass }: { name: string, cost: string, colorClass: string }) {
  const { t } = useLanguage()
  return (
    <Card className={`bg-[rgba(2,6,23,0.8)] backdrop-blur-lg border border-[#393939] shadow-[0_0_15px_rgba(0,0,0,0.5)] p-2 min-w-[120px] rounded-lg translate-x-4 -translate-y-4`}>
      <div className="flex justify-between items-center gap-4 border-b border-[#393939] pb-1 mb-1">
        <span className="font-mono text-(--mastra-text-secondary) text-[10px]">{t('costLabel')}</span>
        <span className="font-bold text-(--mastra-text-primary) text-xs">{cost}</span>
      </div>
      <span className={`block text-[9px] text-${colorClass} font-bold uppercase tracking-wider text-right`}>{name}</span>
    </Card>
  )
}

export default function Routes({ stage }: { stage: number }) {
  const { t } = useLanguage()
  const offset = 0.3

  const pathOptimal = useMemo(() => {
    const pts = []
    for (let i = 0; i <= 60; i++) {
      const t = i / 60
      const x = -15 + t * 30
      const z = -15 + t * 30
      const dev = Math.sin(t * Math.PI) * 8
      const cx = x - dev
      const cz = z + dev
      pts.push(new THREE.Vector3(cx, getHeight(cx, cz) + offset, cz))
    }
    return pts
  }, [])

  const pathShortest = useMemo(() => {
    const pts = []
    for (let i = 0; i <= 60; i++) {
      const t = i / 60
      const cx = -15 + t * 30
      const cz = -15 + t * 30
      pts.push(new THREE.Vector3(cx, getHeight(cx, cz) + offset, cz))
    }
    return pts
  }, [])

  const pathThermal = useMemo(() => {
    const pts = []
    for (let i = 0; i <= 60; i++) {
      const t = i / 60
      const x = -15 + t * 30
      const z = -15 + t * 30
      const dev = Math.sin(t * Math.PI) * -12 // wider opposite detour
      const cx = x - dev
      const cz = z + dev
      pts.push(new THREE.Vector3(cx, getHeight(cx, cz) + offset, cz))
    }
    return pts
  }, [])

  if (stage < 3) return null

  return (
    <group position={[0, -2, 0]}>
       <Line 
        points={pathOptimal}       
        color="#ffa500"                   
        lineWidth={4}                   
        dashed={false}
       />
       {stage >= 4 && (
         <Html position={pathOptimal[pathOptimal.length - 1]} zIndexRange={[100, 0]}>
            <RouteTooltip name={t('profOptimalName')} cost="590,502" colorClass="neon-orange" />
         </Html>
       )}

       <Line 
        points={pathShortest}       
        color="#00ffff"                   
        lineWidth={2}                   
        dashed={true}
        dashSize={1}
        dashScale={2}
       />
       {stage >= 4 && (
         <Html position={pathShortest[pathShortest.length - 1]} zIndexRange={[100, 0]}>
            <RouteTooltip name={t('profShortestName')} cost="1,024,103" colorClass="neon-cyan" />
         </Html>
       )}

       <Line 
        points={pathThermal}       
        color="#ff00ff"                   
        lineWidth={2}                   
        dashed={true}
        dashSize={0.5}
        dashScale={1}
       />
       {stage >= 4 && (
         <Html position={pathThermal[pathThermal.length - 1]} zIndexRange={[100, 0]}>
            <RouteTooltip name={t('profThermalName')} cost="890,200" colorClass="neon-magenta" />
         </Html>
       )}
    </group>
  )
}
