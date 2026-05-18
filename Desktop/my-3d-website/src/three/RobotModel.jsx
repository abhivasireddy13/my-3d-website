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
      const wave = names.find(n => /wave/i.test(n))
      const target = wave || names[0]
      actions[target]?.reset().fadeIn(0.3).play()
    } else {
      const idle = names.find(n => /idle/i.test(n)) || names[0]
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

function FloatingParticles() {
  const COUNT = 800
  const positions = useMemo(() => {
    const arr = new Float32Array(COUNT * 3)
    for (let i = 0; i < COUNT; i++) {
      const r = 1.8 + Math.random() * 1.2
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      arr[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) + 0.5
      arr[i * 3 + 2] = r * Math.cos(phi)
    }
    return arr
  }, [])

  const ref = useRef()
  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.04
      ref.current.rotation.x += delta * 0.015
    }
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={COUNT} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial size={0.012} color="#00e5ff" transparent opacity={0.35} sizeAttenuation />
    </points>
  )
}

function CyanRing() {
  const ref = useRef()
  useFrame((_, delta) => {
    if (ref.current) ref.current.rotation.z += delta * 0.22
  })
  return (
    <mesh ref={ref} rotation={[Math.PI / 2.2, 0, 0]} position={[0, -0.4, 0]}>
      <torusGeometry args={[1.65, 0.008, 8, 160]} />
      <meshBasicMaterial color="#00e5ff" transparent opacity={0.5} />
    </mesh>
  )
}

export default function RobotModel() {
  const [hovered, setHovered] = useState(false)

  return (
    <>
      <ambientLight intensity={0.55} />
      {/* Key light — warm-ish from upper front-left */}
      <pointLight position={[-2.5, 4, 3]}  intensity={3.5} color="#e0f4ff" distance={14} decay={2} />
      {/* Cyan rim — right side */}
      <pointLight position={[3, 2, 1]}     intensity={2.5} color="#00e5ff" distance={12} decay={2} />
      {/* Purple fill — left back */}
      <pointLight position={[-3, 0, -2]}   intensity={1.8} color="#7928ca" distance={12} decay={2} />
      {/* Warm underlight */}
      <pointLight position={[0, -2, 4]}    intensity={1.2} color="#ffffff" distance={8}  decay={2} />
      <Robot hovered={hovered} setHovered={setHovered} />
      <FloatingParticles />
      <CyanRing />
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
