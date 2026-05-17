import { useEffect, useRef, Suspense } from 'react'
import { Canvas } from '@react-three/fiber'
import { motion } from 'framer-motion'
import { gsap } from 'gsap'
import FaceModel from '../three/FaceModel'
import NeuralCanvas from './NeuralCanvas'

const TITLE = 'VASIREDDY ABHISHEK SAI'
const ACCENT = '#00d4ff'

function GlitchText({ text }) {
  const ref = useRef(null)

  useEffect(() => {
    const chars = ref.current?.querySelectorAll('.char')
    if (!chars?.length) return

    gsap.set(chars, { y: 90, opacity: 0 })
    gsap.to(chars, {
      y: 0,
      opacity: 1,
      duration: 0.75,
      stagger: 0.028,
      ease: 'power4.out',
      delay: 0.4,
      onComplete: () => glitch(),
    })

    const glitch = () => {
      const tl = gsap.timeline()
      const subset = Array.from(chars).filter(() => Math.random() > 0.7)
      tl.to(subset, { x: () => (Math.random() - 0.5) * 6, color: ACCENT, duration: 0.06, stagger: 0.01 })
        .to(subset, { x: () => (Math.random() - 0.5) * 4, color: '#FFFFFF', duration: 0.06, stagger: 0.01 })
        .to(subset, { x: 0, color: '#FFFFFF', duration: 0.08, stagger: 0.01 })
    }
    const interval = setInterval(glitch, 4000)
    return () => clearInterval(interval)
  }, [])

  return (
    <h1
      ref={ref}
      style={{
        fontFamily: 'Space Grotesk',
        fontSize: 'clamp(2.2rem, 5.5vw, 5.5rem)',
        fontWeight: 700,
        lineHeight: 1.05,
        letterSpacing: '-0.03em',
        color: '#FFFFFF',
        marginBottom: '1.5rem',
        userSelect: 'none',
      }}
    >
      {text.split('').map((ch, i) => (
        <span
          key={i}
          style={{ display: 'inline-block', overflow: 'hidden', verticalAlign: 'bottom' }}
        >
          <span className="char" style={{ display: 'inline-block' }}>
            {ch === ' ' ? ' ' : ch}
          </span>
        </span>
      ))}
    </h1>
  )
}

function HeroContent() {
  const subtitleRef = useRef(null)
  const btnRef = useRef(null)
  const tagRef = useRef(null)

  useEffect(() => {
    gsap.from([tagRef.current, subtitleRef.current, btnRef.current], {
      y: 30,
      opacity: 0,
      duration: 0.7,
      stagger: 0.15,
      ease: 'power3.out',
      delay: 1.5,
    })
  }, [])

  return (
    <div
      style={{
        position: 'relative',
        zIndex: 10,
        padding: '0 clamp(1.5rem, 6vw, 7rem)',
        maxWidth: '58%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
      className="hero-text-block"
    >
      {/* Role badge */}
      <div ref={tagRef} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem', opacity: 0 }}>
        <span
          style={{
            display: 'inline-block',
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: ACCENT,
            boxShadow: `0 0 10px ${ACCENT}, 0 0 20px rgba(0,212,255,0.5)`,
            animation: 'pulse-glow 2s ease-in-out infinite',
          }}
        />
        <span style={{ fontFamily: 'Inter', fontSize: '0.8rem', color: '#888888', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
          AI / ML Engineer
        </span>
      </div>

      <GlitchText text={TITLE} />

      <p
        ref={subtitleRef}
        style={{
          fontFamily: 'Inter',
          fontSize: 'clamp(1rem, 1.5vw, 1.25rem)',
          color: '#888888',
          marginBottom: '2.5rem',
          lineHeight: 1.6,
          maxWidth: '500px',
          opacity: 0,
        }}
      >
        Building Intelligent Systems<span style={{ color: ACCENT, margin: '0 0.5rem' }}>·</span>
        Computer Vision<span style={{ color: ACCENT, margin: '0 0.5rem' }}>·</span>LLM Applications
      </p>

      <div ref={btnRef} style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', opacity: 0 }}>
        <HeroBtn
          primary
          onClick={() => document.getElementById('projects')?.scrollIntoView({ behavior: 'smooth' })}
        >
          View My Work →
        </HeroBtn>
        <HeroBtn
          onClick={() => document.getElementById('contact')?.scrollIntoView({ behavior: 'smooth' })}
        >
          Get In Touch →
        </HeroBtn>
      </div>
    </div>
  )
}

function HeroBtn({ children, onClick, primary }) {
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    const over = () => {
      el.style.transform = 'scale(1.04) translateY(-1px)'
      if (primary) el.style.boxShadow = `0 8px 30px rgba(0,212,255,0.4)`
      else el.style.boxShadow = `0 0 20px rgba(0,212,255,0.15)`
    }
    const out = () => {
      el.style.transform = 'scale(1) translateY(0)'
      el.style.boxShadow = 'none'
    }
    el.addEventListener('mouseenter', over)
    el.addEventListener('mouseleave', out)
    return () => { el.removeEventListener('mouseenter', over); el.removeEventListener('mouseleave', out) }
  }, [primary])

  return (
    <button
      ref={ref}
      onClick={onClick}
      style={{
        background: primary ? ACCENT : 'transparent',
        border: primary ? 'none' : `1.5px solid rgba(0,212,255,0.35)`,
        color: primary ? '#0a0a0f' : '#FFFFFF',
        fontFamily: 'Inter',
        fontWeight: primary ? 700 : 500,
        fontSize: 'clamp(0.85rem, 1vw, 0.95rem)',
        padding: '0.875rem 2rem',
        borderRadius: '999px',
        transition: 'all 0.25s ease',
        letterSpacing: '0.01em',
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
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
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        background: 'linear-gradient(135deg, #0a0a0f 0%, #0d1b2a 100%)',
      }}
    >
      {/* Neural network background */}
      <NeuralCanvas />

      {/* Radial gradient vignette */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(ellipse 70% 80% at 70% 50%, transparent 30%, rgba(10,10,15,0.85) 100%)',
          zIndex: 1,
          pointerEvents: 'none',
        }}
      />

      {/* Gradient bottom fade */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: '180px',
          background: 'linear-gradient(to top, #0a0a0f, transparent)',
          zIndex: 2,
          pointerEvents: 'none',
        }}
      />

      {/* Three.js face — right side */}
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          width: '52%',
          height: '100%',
          zIndex: 3,
        }}
        className="face-canvas-wrapper"
      >
        <Canvas camera={{ position: [0, 0, 6], fov: 50 }} gl={{ antialias: true, alpha: true }}>
          <ambientLight intensity={0.5} />
          <pointLight position={[3, 3, 3]} intensity={1.2} color="#00d4ff" />
          <pointLight position={[-3, -2, 2]} intensity={0.5} color="#7928ca" />
          <pointLight position={[0, -3, 4]} intensity={0.3} color="#ffffff" />
          <Suspense fallback={null}>
            <FaceModel />
          </Suspense>
        </Canvas>
      </div>

      {/* Hero text content */}
      <HeroContent />

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2.2, duration: 0.8 }}
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
        <span style={{ fontFamily: 'Inter', fontSize: '0.7rem', color: '#444', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
          Scroll
        </span>
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ repeat: Infinity, duration: 1.5, ease: 'easeInOut' }}
          style={{ width: '1px', height: '40px', background: `linear-gradient(to bottom, ${ACCENT}, transparent)` }}
        />
      </motion.div>

      <style>{`
        @media (max-width: 768px) {
          .face-canvas-wrapper { width: 100% !important; opacity: 0.22; }
          .hero-text-block { max-width: 100% !important; }
        }
        @keyframes pulse-glow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </section>
  )
}
