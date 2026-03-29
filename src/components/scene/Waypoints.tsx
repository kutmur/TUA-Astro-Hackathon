import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'
import { getHeight } from '../../lib/terrainMath'

export default function Waypoints({ stage }: { stage: number }) {
  const groupA = useRef<THREE.Group>(null)
  const groupB = useRef<THREE.Group>(null)

  // Target positions (on terrain exactly matching noise function)
  const xA = -15, zA = -15
  const xB = 15, zB = 15
  
  // Apply the same -2 offset that LunarTerrain's group has, then float above
  const yA = getHeight(xA, zA) - 2
  const yB = getHeight(xB, zB) - 2
  const hoverOffset = 1.0

  const posA: [number, number, number] = [xA, yA + hoverOffset, zA]
  const posB: [number, number, number] = [xB, yB + hoverOffset, zB]

  useFrame(({ clock }, delta) => {
    if (stage >= 2) {
      const time = clock.getElapsedTime()
      // Small vertical floating animation (subtle offset)
      const floatA = Math.sin(time * 2) * 0.2
      const floatB = Math.sin(time * 2 + Math.PI) * 0.2

      if (groupA.current) {
        if (groupA.current.position.y > posA[1] + floatA) {
          groupA.current.position.y -= delta * 30
        } else {
          groupA.current.position.y = posA[1] + floatA
        }
      }
      if (groupB.current) {
        if (groupB.current.position.y > posB[1] + floatB) {
          groupB.current.position.y -= delta * 25
        } else {
          groupB.current.position.y = posB[1] + floatB
        }
      }
    }
  })

  if (stage < 2) return null

  return (
    <>
      <group ref={groupA} position={[posA[0], posA[1] + 40, posA[2]]}>
        <mesh>
          <sphereGeometry args={[0.5, 32, 32]} />
          <meshBasicMaterial color="#00ffff" toneMapped={false} />
        </mesh>
        <pointLight color="#00ffff" intensity={2} distance={10} visible={stage >= 2} />
      </group>
      <group ref={groupB} position={[posB[0], posB[1] + 40, posB[2]]}>
        <mesh>
          <sphereGeometry args={[0.5, 32, 32]} />
          <meshBasicMaterial color="#ff00ff" toneMapped={false} />
        </mesh>
        <pointLight color="#ff00ff" intensity={2} distance={10} visible={stage >= 2} />
      </group>
    </>
  )
}
