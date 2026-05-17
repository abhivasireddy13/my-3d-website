import { useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { useTexture } from '@react-three/drei'
import * as THREE from 'three'
import abhiImg from '../assets/abhi.jpg'

function TexturedSphere({ meshRef }) {
  const texture = useTexture(abhiImg)
  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[1.9, 64, 64]} />
      <meshStandardMaterial map={texture} roughness={0.3} metalness={0.08} />
    </mesh>
  )
}

export default function FaceModel() {
  const groupRef = useRef()
  const meshRef  = useRef()
  const { mouse } = useThree()

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += (mouse.x * 0.8 - groupRef.current.rotation.y) * 0.04
      groupRef.current.rotation.x += (-mouse.y * 0.4 - groupRef.current.rotation.x) * 0.04
    }
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.22
    }
  })

  return (
    <group ref={groupRef}>
      {/* Outer glow shell */}
      <mesh>
        <sphereGeometry args={[2.18, 32, 32]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0.04} side={THREE.BackSide} />
      </mesh>

      {/* Inner glow shell */}
      <mesh>
        <sphereGeometry args={[2.05, 32, 32]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0.07} side={THREE.BackSide} />
      </mesh>

      {/* Photo-textured sphere */}
      <TexturedSphere meshRef={meshRef} />

      {/* Cyan orbit ring */}
      <mesh rotation={[Math.PI / 5, 0, 0]}>
        <torusGeometry args={[2.45, 0.013, 8, 120]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0.55} />
      </mesh>

      {/* Thin secondary ring */}
      <mesh rotation={[-Math.PI / 4, Math.PI / 6, 0]}>
        <torusGeometry args={[2.6, 0.007, 8, 120]} />
        <meshBasicMaterial color="#7928ca" transparent opacity={0.35} />
      </mesh>
    </group>
  )
}
