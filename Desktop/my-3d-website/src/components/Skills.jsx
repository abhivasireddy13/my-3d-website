import { Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { motion } from 'framer-motion'
import SkillSphere from '../three/SkillSphere'

const SKILLS = [
  { name: 'Python',      level: 95, position: [-4.5,  2.0,  0.3] },
  { name: 'TensorFlow',  level: 85, position: [-1.5,  2.0, -0.2] },
  { name: 'PyTorch',     level: 88, position: [ 1.5,  2.0,  0.4] },
  { name: 'OpenCV',      level: 80, position: [ 4.5,  2.0, -0.1] },
  { name: 'LangChain',   level: 82, position: [-4.5,  0.0,  0.2] },
  { name: 'HuggingFace', level: 78, position: [-1.5,  0.0,  0.5] },
  { name: 'FastAPI',     level: 75, position: [ 1.5,  0.0, -0.3] },
  { name: 'Docker',      level: 70, position: [ 4.5,  0.0,  0.1] },
  { name: 'PostgreSQL',  level: 72, position: [-4.5, -2.0, -0.2] },
  { name: 'React',       level: 68, position: [-1.5, -2.0,  0.3] },
  { name: 'Git',         level: 90, position: [ 1.5, -2.0,  0.0] },
  { name: 'AWS',         level: 65, position: [ 4.5, -2.0,  0.4] },
]

function SphereLights() {
  return (
    <>
      <ambientLight intensity={0.3} />
      <pointLight position={[0, 5, 5]}   intensity={1.2} color="#00d4ff" />
      <pointLight position={[-6, -4, 3]} intensity={0.5} color="#7928ca" />
      <pointLight position={[6, 4, -2]}  intensity={0.4} color="#FFFFFF" />
    </>
  )
}

export default function Skills() {
  return (
    <section
      id="skills"
      style={{
        position: 'relative',
        padding: 'clamp(5rem, 10vw, 9rem) clamp(1.5rem, 6vw, 7rem)',
        background: '#0d1117',
        overflow: 'hidden',
      }}
    >
      {/* Grid background */}
      <div
        className="grid-bg"
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0 }}
      />

      {/* Hexagon grid accent */}
      <svg
        style={{ position: 'absolute', top: 0, right: 0, opacity: 0.04, pointerEvents: 'none' }}
        width="400" height="400" viewBox="0 0 400 400"
      >
        {[0,1,2,3,4,5].map(row =>
          [0,1,2,3].map(col => {
            const x = col * 80 + (row % 2) * 40 + 20
            const y = row * 70 + 20
            const pts = Array.from({length:6}, (_,i) => {
              const a = (Math.PI/180)*(60*i-30)
              return `${x+32*Math.cos(a)},${y+32*Math.sin(a)}`
            }).join(' ')
            return <polygon key={`${row}-${col}`} points={pts} fill="none" stroke="#00d4ff" strokeWidth="1" />
          })
        )}
      </svg>

      {/* Glow blob */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '800px',
        height: '800px',
        background: 'radial-gradient(circle, rgba(0,212,255,0.04) 0%, transparent 70%)',
        pointerEvents: 'none',
        zIndex: 0,
      }} />

      <div style={{ position: 'relative', zIndex: 1 }}>
        {/* Section header */}
        <motion.p
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          style={{ fontFamily: 'Inter', fontSize: '0.75rem', color: '#00d4ff', letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '1rem' }}
        >
          02 — Skills
        </motion.p>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
          <motion.h2
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            style={{ fontFamily: 'Space Grotesk', fontSize: 'clamp(2rem, 4vw, 3.5rem)', fontWeight: 700, letterSpacing: '-0.03em', color: '#e2e8f0' }}
          >
            Technologies<br />
            <span style={{ color: '#00d4ff' }}>I Work With.</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.3, duration: 0.6 }}
            style={{ fontFamily: 'Inter', fontSize: '0.875rem', color: '#555', maxWidth: '280px', lineHeight: 1.6, textAlign: 'right' }}
          >
            Hover over a sphere to see my proficiency level. Each orb is a tool I use daily.
          </motion.p>
        </div>

        {/* 3D Canvas */}
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 1, ease: [0.22, 1, 0.36, 1] }}
          style={{
            width: '100%',
            height: 'clamp(420px, 55vw, 640px)',
            borderRadius: '12px',
            border: '1px solid rgba(0,212,255,0.12)',
            overflow: 'hidden',
            background: 'rgba(10,10,15,0.7)',
            boxShadow: '0 0 40px rgba(0,212,255,0.05)',
          }}
        >
          <Canvas
            camera={{ position: [0, 0, 10], fov: 55 }}
            gl={{ antialias: true, alpha: true }}
          >
            <SphereLights />
            <Suspense fallback={null}>
              {SKILLS.map((skill, i) => (
                <SkillSphere
                  key={skill.name}
                  name={skill.name}
                  level={skill.level}
                  position={skill.position}
                  index={i}
                />
              ))}
            </Suspense>
          </Canvas>
        </motion.div>

        {/* Legend bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4, duration: 0.6 }}
          style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem', flexWrap: 'wrap' }}
        >
          {SKILLS.map((s) => (
            <span
              key={s.name}
              style={{
                fontFamily: 'Inter',
                fontSize: '0.78rem',
                color: '#666',
                background: '#111827',
                border: '1px solid rgba(0,212,255,0.12)',
                borderRadius: '999px',
                padding: '0.3rem 0.85rem',
              }}
            >
              {s.name}
            </span>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
