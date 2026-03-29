import { useMemo } from 'react'
import * as THREE from 'three'
import { Line } from '@react-three/drei'

export default function Routes({ stage }: { stage: number }) {
  // Mock path coordinates (A to B) adjusting for terrain height roughly
  const pathOptimal = useMemo(() => [
    [-15, 0.5, -15],
    [-8, 1.2, -8],
    [-2, -0.5, -2],
    [5, -2, 5],
    [10, -1, 10],
    [15, -0.5, 15]
  ].map(p => new THREE.Vector3(...p)), [])

  const pathShortest = useMemo(() => [
    [-15, 0.5, -15],
    [0, 2, 0], 
    [15, -0.5, 15]
  ].map(p => new THREE.Vector3(...p)), [])

  const pathThermal = useMemo(() => [
    [-15, 0.5, -15],
    [-10, 0, 10], 
    [0, -1.5, 20],
    [15, -0.5, 15]
  ].map(p => new THREE.Vector3(...p)), [])

  if (stage < 3) return null

  return (
    <group position={[0, -1.8, 0]}>
       <Line 
        points={pathOptimal}       
        color="#ffa500"                   
        lineWidth={4}                   
        dashed={false}
       />
       <Line 
        points={pathShortest}       
        color="#00ffff"                   
        lineWidth={2}                   
        dashed={true}
        dashSize={1}
        dashScale={2}
       />
       <Line 
        points={pathThermal}       
        color="#ff00ff"                   
        lineWidth={2}                   
        dashed={true}
        dashSize={0.5}
        dashScale={1}
       />
    </group>
  )
}
