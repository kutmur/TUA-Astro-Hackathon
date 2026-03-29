import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import * as THREE from 'three'

export default function Waypoints({ stage }: { stage: number }) {
  const groupA = useRef<THREE.Group>(null)
  const groupB = useRef<THREE.Group>(null)

  // Target positions (on terrain roughly)
  const posA: [number, number, number] = [-15, 0.5, -15]
  const posB: [number, number, number] = [15, -0.5, 15]

  useFrame((_, delta) => {
    if (stage >= 2) {
      if (groupA.current) {
        if (groupA.current.position.y > posA[1]) {
          groupA.current.position.y -= delta * 30
        } else {
          groupA.current.position.y = posA[1]
        }
      }
      if (groupB.current) {
        if (groupB.current.position.y > posB[1]) {
          groupB.current.position.y -= delta * 25
        } else {
          groupB.current.position.y = posB[1]
        }
      }
    }
  })

  if (stage < 2) return null

  return (
    <>
      <group ref={groupA} position={[posA[0], posA[1] + 40, posA[2]]}>
        <mesh>
          <sphereGeometry args={[0.5, 16, 16]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
        <pointLight color="#00ffff" intensity={2} distance={10} visible={stage >= 2} />
      </group>
      <group ref={groupB} position={[posB[0], posB[1] + 40, posB[2]]}>
        <mesh>
          <sphereGeometry args={[0.5, 16, 16]} />
          <meshBasicMaterial color="#ffffff" />
        </mesh>
        <pointLight color="#ff00ff" intensity={2} distance={10} visible={stage >= 2} />
      </group>
    </>
  )
}
