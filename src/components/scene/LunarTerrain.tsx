import { useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'

export default function LunarTerrain({ stage }: { stage: number }) {
  const meshRef = useRef<THREE.Mesh>(null)

  const grid = 64
  const size = 60
  
  const { positions, colors, indices } = useMemo(() => {
    const pos = []
    const col = []
    const ind = []

    const colorDeep = new THREE.Color('#0f172a') // slage-900
    const colorMid = new THREE.Color('#1e293b')  // slate-800
    const colorHigh = new THREE.Color('#334155') // slate-700

    for (let i = 0; i <= grid; i++) {
        for (let j = 0; j <= grid; j++) {
            const x = (i / grid - 0.5) * size
            const z = (j / grid - 0.5) * size
            
            // Perlin-like
            const nx = i / 10
            const nz = j / 10
            let y = Math.sin(nx)*Math.cos(nz)*2 + Math.sin(nx*2.5 + nz)*1
            
            // Crater roughly in center-ish
            const cx = x + 5
            const cz = z - 5
            const cr = Math.sqrt(cx*cx + cz*cz)
            if (cr < 15) {
                y -= (15 - cr) * 0.8
            }

            pos.push(x, y, z)

            const normY = Math.max(0, Math.min(1, (y + 10) / 15))
            const c = colorDeep.clone().lerp(colorMid, normY * 2)
            if(normY > 0.5) c.lerp(colorHigh, (normY - 0.5)*2)
            col.push(c.r, c.g, c.b)
        }
    }

    for (let i = 0; i < grid; i++) {
        for (let j = 0; j < grid; j++) {
            const a = i * (grid + 1) + j
            const b = i * (grid + 1) + j + 1
            const c = (i + 1) * (grid + 1) + j
            const d = (i + 1) * (grid + 1) + j + 1

            ind.push(a, b, d)
            ind.push(a, d, c)
        }
    }

    return {
        positions: new Float32Array(pos),
        colors: new Float32Array(col),
        indices: new Uint16Array(ind)
    }
  }, [])

  const materialRef = useRef<THREE.MeshStandardMaterial>(null)
  const wireframeRef = useRef<THREE.MeshBasicMaterial>(null)

  useFrame((_, delta) => {
    if (stage >= 1) {
      if (materialRef.current && materialRef.current.opacity < 1) {
        materialRef.current.opacity += delta * 0.5
      }
      if (wireframeRef.current && wireframeRef.current.opacity < 0.15) {
        wireframeRef.current.opacity += delta * 0.1
      }
    }
  })

  return (
    <group position={[0, -2, 0]}>
      <mesh ref={meshRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
          <bufferAttribute attach="attributes-color" args={[colors, 3]} />
          <bufferAttribute attach="index" args={[indices, 1]} />
        </bufferGeometry>
        <meshStandardMaterial 
          ref={materialRef}
          vertexColors 
          flatShading 
          transparent 
          opacity={0}
          side={THREE.DoubleSide}
        />
      </mesh>
      <mesh>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
          <bufferAttribute attach="index" args={[indices, 1]} />
        </bufferGeometry>
        <meshBasicMaterial 
          ref={wireframeRef}
          color="#38bdf8" 
          wireframe 
          transparent 
          opacity={0} 
        />
      </mesh>
    </group>
  )
}
