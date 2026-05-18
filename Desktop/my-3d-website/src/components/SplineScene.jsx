export default function SplineScene({ style }) {
  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', ...style }}>
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
          0%,100% { transform: translateY(0) scale(1); box-shadow: 0 0 80px rgba(0,229,255,0.18), 0 0 160px rgba(0,229,255,0.07); }
          50%      { transform: translateY(-18px) scale(1.04); box-shadow: 0 0 110px rgba(0,229,255,0.28), 0 0 200px rgba(0,229,255,0.1); }
        }
      `}</style>
    </div>
  )
}
