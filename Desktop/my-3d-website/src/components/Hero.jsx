import { useState, useEffect, Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { motion, AnimatePresence } from 'framer-motion'
import FaceModel from '../three/FaceModel'

const ROLES = ['AI/ML Engineer', 'LLM Engineer', 'MLOps Engineer', 'GenAI Developer']
const ACCENT = '#00e5ff'

function RoleRotator() {
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setIdx(i => (i + 1) % ROLES.length), 2800)
    return () => clearInterval(t)
  }, [])

  return (
    <div style={{ height: '2.2rem', overflow: 'hidden', marginTop: '0.75rem' }}>
      <AnimatePresence mode="wait">
        <motion.p
          key={idx}
          initial={{ y: 36, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -36, opacity: 0 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          style={{
            fontFamily: 'Inter',
            fontSize: 'clamp(1rem, 1.8vw, 1.35rem)',
            fontWeight: 500,
            color: ACCENT,
            letterSpacing: '0.04em',
            margin: 0,
          }}
        >
          {ROLES[idx]}
        </motion.p>
      </AnimatePresence>
    </div>
  )
}

export default function Hero() {
  return (
    <section
      id="hero"
      style={{
        position: 'relative',
        height: '100vh',
        minHeight: '600px',
        display: 'flex',
        alignItems: 'center',
        background: '#0a0a0f',
        overflow: 'clip',
      }}
    >
      {/* Radial glow */}
      <div style={{
        position: 'absolute',
        inset: 0,
        background: 'radial-gradient(ellipse 60% 70% at 65% 50%, rgba(0,229,255,0.07) 0%, transparent 70%)',
        pointerEvents: 'none',
        zIndex: 0,
      }} />

      {/* Bottom fade */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: '160px',
        background: 'linear-gradient(to top, #0a0a0f, transparent)',
        zIndex: 4,
        pointerEvents: 'none',
      }} />

      {/* Left text block */}
      <div
        className="hero-left"
        style={{
          position: 'relative',
          zIndex: 10,
          padding: '0 clamp(2rem, 8vw, 9rem)',
          flex: '0 0 52%',
          maxWidth: '52%',
        }}
      >
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          style={{
            fontFamily: 'Inter',
            fontSize: 'clamp(0.95rem, 1.4vw, 1.15rem)',
            color: '#555',
            marginBottom: '0.5rem',
            letterSpacing: '0.02em',
          }}
        >
          Hello! I'm
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          <h1
            style={{
              fontFamily: 'Space Grotesk',
              fontSize: 'clamp(3.5rem, 7.5vw, 8.5rem)',
              fontWeight: 800,
              lineHeight: 0.9,
              letterSpacing: '-0.04em',
              color: '#ffffff',
              margin: 0,
            }}
          >
            ABHI<br />
            <span style={{ color: ACCENT }}>VASIREDDY</span>
          </h1>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7, duration: 0.5 }}
        >
          <RoleRotator />
        </motion.div>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.6 }}
          style={{
            fontFamily: 'Inter',
            fontSize: 'clamp(0.9rem, 1.3vw, 1.05rem)',
            color: '#555',
            lineHeight: 1.7,
            maxWidth: '420px',
            marginTop: '1.5rem',
          }}
        >
          Building production-grade ML systems — RAG pipelines, LLM fine-tuning,
          and MLOps infrastructure at scale.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.05, duration: 0.55 }}
          style={{ marginTop: '2.25rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}
        >
          <button
            onClick={() => document.getElementById('projects')?.scrollIntoView({ behavior: 'smooth' })}
            style={{
              padding: '0.85rem 2rem',
              borderRadius: '999px',
              background: ACCENT,
              color: '#0a0a0f',
              fontFamily: 'Inter',
              fontWeight: 700,
              fontSize: '0.88rem',
              border: 'none',
              cursor: 'pointer',
              letterSpacing: '0.02em',
              transition: 'box-shadow 0.25s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 0 28px rgba(0,229,255,0.55)` }}
            onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none' }}
          >
            View My Work →
          </button>
          <button
            onClick={() => document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })}
            style={{
              padding: '0.85rem 2rem',
              borderRadius: '999px',
              background: 'transparent',
              color: '#fff',
              fontFamily: 'Inter',
              fontWeight: 500,
              fontSize: '0.88rem',
              border: '1.5px solid rgba(0,229,255,0.3)',
              cursor: 'pointer',
              letterSpacing: '0.02em',
              transition: 'all 0.25s ease',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = ACCENT; e.currentTarget.style.color = ACCENT }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(0,229,255,0.3)'; e.currentTarget.style.color = '#fff' }}
          >
            Get In Touch
          </button>
        </motion.div>
      </div>

      {/* Three.js 3D sphere — right side */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 1.2 }}
        className="hero-canvas"
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          width: '52%',
          height: '100%',
          zIndex: 3,
        }}
      >
        <Canvas
          camera={{ position: [0, 0, 6], fov: 50 }}
          gl={{ antialias: true, alpha: true }}
          style={{ width: '100%', height: '100%' }}
        >
          <ambientLight intensity={0.45} />
          <pointLight position={[3, 3, 3]}   intensity={1.4} color="#00e5ff" />
          <pointLight position={[-3, -2, 2]} intensity={0.6} color="#7928ca" />
          <pointLight position={[0, -3, 4]}  intensity={0.3} color="#ffffff" />
          <Suspense fallback={null}>
            <FaceModel />
          </Suspense>
        </Canvas>
      </motion.div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 0.8 }}
        style={{
          position: 'absolute',
          bottom: '2.5rem',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '0.5rem',
        }}
      >
        <span style={{ fontFamily: 'Inter', fontSize: '0.65rem', color: '#333', letterSpacing: '0.18em', textTransform: 'uppercase' }}>
          Scroll
        </span>
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
          style={{ width: '1px', height: '36px', background: `linear-gradient(to bottom, ${ACCENT}, transparent)` }}
        />
      </motion.div>

      <style>{`
        @media (max-width: 768px) {
          .hero-left   { flex: 0 0 100% !important; max-width: 100% !important; }
          .hero-canvas { display: none !important; }
        }
      `}</style>
    </section>
  )
}
