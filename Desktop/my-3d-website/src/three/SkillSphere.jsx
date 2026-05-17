import { useRef, useState, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Text } from '@react-three/drei'
import * as THREE from 'three'

export default function SkillSphere({ position, name, level, index }) {
  const groupRef = useRef()
  const meshRef = useRef()
  const ringRef = useRef()
  const [hovered, setHovered] = useState(false)
  const targetScale = useRef(new THREE.Vector3(1, 1, 1))

  const glowColor = useMemo(() => new THREE.Color('#00d4ff'), [])
  const darkColor = useMemo(() => new THREE.Color('#0d1829'), [])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    if (groupRef.current) {
      groupRef.current.position.y = position[1] + Math.sin(t * 0.7 + index * 1.1) * 0.28
    }
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.007
      meshRef.current.rotation.x += 0.003
      targetScale.current.setScalar(hovered ? 1.28 : 1)
      meshRef.current.scale.lerp(targetScale.current, 0.1)

      const mat = meshRef.current.material
      mat.emissiveIntensity = THREE.MathUtils.lerp(mat.emissiveIntensity, hovered ? 0.7 : 0.1, 0.1)
      mat.color.lerp(hovered ? glowColor : darkColor, 0.08)
    }
    if (ringRef.current) {
      ringRef.current.rotation.z += 0.02
      ringRef.current.material.opacity = THREE.MathUtils.lerp(ringRef.current.material.opacity, hovered ? 0.9 : 0, 0.1)
    }
  })

  return (
    <group ref={groupRef} position={[position[0], position[1], position[2]]}>
      {/* Main sphere */}
      <mesh
        ref={meshRef}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <sphereGeometry args={[0.72, 40, 40]} />
        <meshStandardMaterial
          color="#0d1829"
          emissive="#00d4ff"
          emissiveIntensity={0.1}
          roughness={0.15}
          metalness={0.95}
        />
      </mesh>

      {/* Glow ring on hover */}
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.95, 0.018, 8, 80]} />
        <meshBasicMaterial color="#00d4ff" transparent opacity={0} />
      </mesh>

      {/* Skill name label */}
      <Text
        position={[0, -0.95, 0]}
        fontSize={0.18}
        color={hovered ? '#00d4ff' : '#AAAAAA'}
        anchorX="center"
        anchorY="middle"
        maxWidth={2}
        textAlign="center"
        font="https://fonts.gstatic.com/s/spacegrotesk/v16/V8mDoQDjQSkFtoMM3T6r8E7mF71Q-gozuiqy-oN1m44.woff2"
      >
        {name}
      </Text>

      {/* Level % on hover */}
      {hovered && (
        <Text
          position={[0, 0, 0.78]}
          fontSize={0.22}
          color="#FFFFFF"
          anchorX="center"
          anchorY="middle"
          font="https://fonts.gstatic.com/s/spacegrotesk/v16/V8mDoQDjQSkFtoMM3T6r8E7mF71Q-gozuiqy-oN1m44.woff2"
        >
          {level}%
        </Text>
      )}
    </group>
  )
}
