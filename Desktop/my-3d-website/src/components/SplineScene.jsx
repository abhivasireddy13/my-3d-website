import React, { Suspense, useState, useEffect, useRef } from 'react'
import Spline from '@splinetool/react-spline'

// Verified public scenes — sorted largest → smallest (most detail first)
const SCENES = [
  'https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode', // 1.35 MB — interactive robot (coding-dada)
  'https://prod.spline.design/qZVRVwoO115vt9NN/scene.splinecode', // 906 KB — hero section scene
  'https://prod.spline.design/d54UYJ7lfP9yBrNO/scene.splinecode', // 835 KB — portfolio scene
  'https://prod.spline.design/oQF2wFKmvwQjdZjp/scene.splinecode', // 738 KB — portfolio scene
  'https://prod.spline.design/Nmx4Vyeze9wJ-9zm/scene.splinecode', // 455 KB — fallback scene
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
    <div style={{
      width: '100%', height: '100%',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        width: 'clamp(260px, 38vw, 520px)',
        height: 'clamp(260px, 38vw, 520px)',
        borderRadius: '50%',
        background: 'radial-gradient(circle at 35% 35%, rgba(0,229,255,0.32) 0%, rgba(121,40,202,0.15) 50%, transparent 80%)',
        border: '1px solid rgba(0,229,255,0.3)',
        boxShadow: '0 0 100px rgba(0,229,255,0.22), 0 0 200px rgba(0,229,255,0.09)',
        animation: 'orbFloat 4s ease-in-out infinite',
      }} />
      <style>{`
        @keyframes orbFloat {
          0%,100% { transform: translateY(0) scale(1); }
          50%      { transform: translateY(-22px) scale(1.05); }
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
    timerRef.current = setTimeout(() => {
      if (!loadedRef.current && idx < SCENES.length - 1) setIdx(i => i + 1)
    }, 14000)
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
