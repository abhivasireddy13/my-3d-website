import React, { Suspense, useState, useEffect, useRef } from 'react'
import Spline from '@splinetool/react-spline'

// Public scenes — verified 200 OK with real content sizes
const SCENES = [
  'https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode', // 1.35 MB robot character
  'https://prod.spline.design/Nmx4Vyeze9wJ-9zm/scene.splinecode', // 455 KB scene
]

class SplineBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { caught: false }
  }
  static getDerivedStateFromError() { return { caught: true } }
  componentDidCatch() { this.props.onError?.() }
  render() {
    if (this.state.caught) return null
    return this.props.children
  }
}

function GlowOrb() {
  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{
        width: 'clamp(220px, 30vw, 380px)',
        height: 'clamp(220px, 30vw, 380px)',
        borderRadius: '50%',
        background: 'radial-gradient(circle at 35% 35%, rgba(0,229,255,0.28) 0%, rgba(121,40,202,0.12) 50%, transparent 80%)',
        border: '1px solid rgba(0,229,255,0.25)',
        boxShadow: '0 0 80px rgba(0,229,255,0.18), 0 0 160px rgba(0,229,255,0.07)',
        animation: 'orbFloat 4s ease-in-out infinite',
      }} />
      <style>{`
        @keyframes orbFloat {
          0%,100% { transform: translateY(0) scale(1); }
          50%      { transform: translateY(-18px) scale(1.04); }
        }
      `}</style>
    </div>
  )
}

export default function SplineScene({ style }) {
  const [idx, setIdx] = useState(0)
  const loadedRef = useRef(false)
  const timerRef = useRef(null)

  const tryNext = () => {
    loadedRef.current = false
    clearTimeout(timerRef.current)
    setIdx(i => i + 1)
  }

  useEffect(() => {
    loadedRef.current = false
    // Allow 12 s for the larger scene to download
    timerRef.current = setTimeout(() => {
      if (!loadedRef.current && idx < SCENES.length - 1) setIdx(i => i + 1)
    }, 12000)
    return () => clearTimeout(timerRef.current)
  }, [idx])

  if (idx >= SCENES.length) return <GlowOrb />

  return (
    <div style={{ width: '100%', height: '100%', ...style }}>
      <SplineBoundary key={idx} onError={tryNext}>
        <Suspense fallback={null}>
          <Spline
            scene={SCENES[idx]}
            onLoad={() => {
              loadedRef.current = true
              clearTimeout(timerRef.current)
            }}
            style={{ width: '100%', height: '100%' }}
          />
        </Suspense>
      </SplineBoundary>
    </div>
  )
}
