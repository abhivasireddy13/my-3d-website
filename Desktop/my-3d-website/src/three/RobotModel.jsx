import { useRef, useEffect, useState, useMemo } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { useGLTF, useAnimations, ContactShadows } from '@react-three/drei'
import * as THREE from 'three'

const MODEL_URL = `${import.meta.env.BASE_URL}robot.glb`

function Robot({ hovered, setHovered }) {
  const group = useRef()
  const { scene, animations } = useGLTF(MODEL_URL)
  const { actions, names } = useAnimations(animations, group)
  const { mouse } = useThree()

  useEffect(() => {
    scene.traverse(obj => {
      if (obj.isMesh) {
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material]
        mats.forEach(mat => {
          mat.emissive = new THREE.Color('#001a20')
          mat.emissiveIntensity = 0.45
          mat.needsUpdate = true
        })
      }
    })
  }, [scene])

  useEffect(() => {
    if (!names.length) return
    Object.values(actions).forEach(a => a?.fadeOut(0.3))
    if (hovered) {
      const wave = names.find(n => n === 'Wave') || names.find(n => n.toLowerCase().includes('wave'))
      const target = wave || names[0]
      actions[target]?.reset().fadeIn(0.3).play()
    } else {
      const idle = names.find(n => n === 'Idle') || names.find(n => n.toLowerCase().includes('idle')) || names[0]
      actions[idle]?.reset().fadeIn(0.3).play()
    }
  }, [hovered, actions, names])

  useFrame(() => {
    if (!group.current) return
    group.current.rotation.y += (mouse.x * 0.45 - group.current.rotation.y) * 0.05
    group.current.rotation.x += (-mouse.y * 0.1 - group.current.rotation.x) * 0.04
  })

  return (
    <primitive
      ref={group}
      object={scene}
      scale={1.8}
      position={[0, -2.4, 0]}
      onPointerOver={() => setHovered(true)}
      onPointerOut={() => setHovered(false)}
    />
  )
}

function Rings() {
  const r1 = useRef()
  const r2 = useRef()
  const r3 = useRef()

  useFrame((_, delta) => {
    if (r1.current) r1.current.rotation.z += delta * 0.38
    if (r2.current) r2.current.rotation.x += delta * 0.24
    if (r3.current) {
      r3.current.rotation.y += delta * 0.16
      r3.current.rotation.z -= delta * 0.11
    }
  })

  return (
    <>
      <mesh ref={r1} rotation={[Math.PI / 2.3, 0, 0]}>
        <torusGeometry args={[2.3, 0.013, 8, 200]} />
        <meshBasicMaterial color="#00e5ff" transparent opacity={0.6} />
      </mesh>
      <mesh ref={r2} rotation={[0.4, Math.PI / 5, Math.PI / 4.5]}>
        <torusGeometry args={[2.6, 0.008, 8, 200]} />
        <meshBasicMaterial color="#7928ca" transparent opacity={0.4} />
      </mesh>
      <mesh ref={r3} rotation={[Math.PI / 3.5, Math.PI / 7, 0]}>
        <torusGeometry args={[2.85, 0.005, 8, 200]} />
        <meshBasicMaterial color="#00e5ff" transparent opacity={0.22} />
      </mesh>
    </>
  )
}

function Particles() {
  const COUNT = 1200
  const positions = useMemo(() => {
    const arr = new Float32Array(COUNT * 3)
    for (let i = 0; i < COUNT; i++) {
      const r = 2.9 + Math.random() * 0.9
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      arr[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      arr[i * 3 + 2] = r * Math.cos(phi)
    }
    return arr
  }, [])

  const ref = useRef()
  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.032
      ref.current.rotation.x += delta * 0.014
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={COUNT} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.015} color="#00e5ff" transparent opacity={0.42} sizeAttenuation />
    </points>
  )
}

export default function RobotModel() {
  const [hovered, setHovered] = useState(false)

  return (
    <>
      <ambientLight intensity={0.4} />
      <pointLight position={[4, 7, 4]}   intensity={4.0} color="#00e5ff" distance={20} decay={2} />
      <pointLight position={[-4, 2, 3]}  intensity={2.2} color="#7928ca" distance={15} decay={2} />
      <pointLight position={[0, -1, 6]}  intensity={1.5} color="#ffffff" distance={12} decay={2} />
      <spotLight
        position={[0, 12, 2]}
        angle={0.35}
        penumbra={0.9}
        intensity={5}
        color="#00e5ff"
      />
      <Robot hovered={hovered} setHovered={setHovered} />
      <Rings />
      <Particles />
      <ContactShadows
        position={[0, -2.4, 0]}
        opacity={0.5}
        scale={7}
        blur={3}
        far={3.5}
        color="#00aacc"
      />
    </>
  )
}

useGLTF.preload(MODEL_URL)
