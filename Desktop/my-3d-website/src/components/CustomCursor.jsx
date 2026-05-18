import { useEffect, useRef } from 'react'

export default function CustomCursor() {
  const dotRef  = useRef(null)
  const ringRef = useRef(null)

  useEffect(() => {
    const dot  = dotRef.current
    const ring = ringRef.current
    if (!dot || !ring) return

    let mx = 0, my = 0, rx = 0, ry = 0

    const onMove = (e) => {
      mx = e.clientX
      my = e.clientY
      dot.style.transform = `translate(${mx - 4}px, ${my - 4}px)`
    }

    let rafId
    const lerp = () => {
      rx += (mx - rx) * 0.12
      ry += (my - ry) * 0.12
      ring.style.transform = `translate(${rx - 16}px, ${ry - 16}px)`
      rafId = requestAnimationFrame(lerp)
    }
    rafId = requestAnimationFrame(lerp)

    window.addEventListener('mousemove', onMove)
    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(rafId)
    }
  }, [])

  return (
    <>
      <div
        ref={dotRef}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: '#00d4ff',
          pointerEvents: 'none',
          zIndex: 9999,
          mixBlendMode: 'screen',
        }}
      />
      <div
        ref={ringRef}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          border: '1.5px solid rgba(0,212,255,0.5)',
          pointerEvents: 'none',
          zIndex: 9998,
        }}
      />
    </>
  )
}
