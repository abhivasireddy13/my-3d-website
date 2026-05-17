import { motion } from 'framer-motion'

const STATS = [
  { value: '5+',    label: 'Projects Shipped' },
  { value: '3+',    label: 'Internships' },
  { value: '2026',  label: 'Graduate' },
  { value: 'AI/ML', label: 'Focused' },
]

const fadeUp = {
  hidden: { opacity: 0, y: 48 },
  show:   { opacity: 1, y: 0,  transition: { duration: 0.75, ease: [0.22, 1, 0.36, 1] } },
}

const stagger = {
  hidden: {},
  show:   { transition: { staggerChildren: 0.12 } },
}

function NeuralNetworkSVG() {
  const nodes = [
    [80, 60], [200, 40], [320, 80], [440, 50], [560, 70],
    [100, 160], [240, 140], [380, 170], [500, 150],
    [60, 250], [180, 230], [300, 260], [420, 240], [540, 270],
  ]
  const edges = [
    [0,1],[1,2],[2,3],[3,4],[0,5],[1,5],[1,6],[2,6],[2,7],[3,7],[3,8],[4,8],
    [5,9],[5,10],[6,10],[6,11],[7,11],[7,12],[8,12],[8,13],[9,10],[10,11],[11,12],[12,13],
  ]
  return (
    <svg
      width="600"
      height="300"
      viewBox="0 0 600 300"
      style={{ position: 'absolute', top: 0, right: 0, opacity: 0.12, pointerEvents: 'none' }}
    >
      {edges.map(([a, b], i) => (
        <line
          key={i}
          x1={nodes[a][0]} y1={nodes[a][1]}
          x2={nodes[b][0]} y2={nodes[b][1]}
          stroke="#00d4ff"
          strokeWidth="1"
        />
      ))}
      {nodes.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="5" fill="#00d4ff" />
      ))}
    </svg>
  )
}

export default function About() {
  return (
    <section
      id="about"
      style={{
        padding: 'clamp(5rem, 10vw, 9rem) clamp(1.5rem, 6vw, 7rem)',
        background: '#0a0a0f',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Neural network decorative SVG */}
      <NeuralNetworkSVG />

      {/* Accent corner glow */}
      <div style={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: '500px',
        height: '500px',
        background: 'radial-gradient(circle, rgba(0,212,255,0.06) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* Section label */}
      <motion.p
        initial={{ opacity: 0, x: -20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        style={{
          fontFamily: 'Inter',
          fontSize: '0.75rem',
          color: '#00d4ff',
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          marginBottom: '1rem',
        }}
      >
        01 — About
      </motion.p>

      <motion.h2
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        style={{
          fontFamily: 'Space Grotesk',
          fontSize: 'clamp(2rem, 4vw, 3.5rem)',
          fontWeight: 700,
          letterSpacing: '-0.03em',
          color: '#e2e8f0',
          marginBottom: '4rem',
        }}
      >
        The Engineer<br />
        <span style={{ color: '#00d4ff' }}>Behind the Code.</span>
      </motion.h2>

      {/* Two-column layout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: 'clamp(2rem, 5vw, 5rem)',
          alignItems: 'start',
          marginBottom: '4rem',
        }}
      >
        {/* Photo column */}
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <div
            style={{
              width: '100%',
              aspectRatio: '4/5',
              maxWidth: '380px',
              borderRadius: '12px',
              border: '1px solid rgba(0,212,255,0.2)',
              overflow: 'hidden',
              position: 'relative',
              boxShadow: '0 0 40px rgba(0,212,255,0.08)',
            }}
          >
            <img
              src="/assets/abhi.jpg"
              alt="Abhishek Sai Vasireddy"
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
          </div>
        </motion.div>

        {/* Bio column */}
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
          style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', paddingTop: '0.5rem' }}
        >
          <p style={{
            fontFamily: 'Inter',
            fontSize: 'clamp(1rem, 1.3vw, 1.15rem)',
            color: '#CCCCCC',
            lineHeight: 1.8,
          }}>
            Final-year B.Tech CSE (AI & ML) student at{' '}
            <span style={{ color: '#00d4ff', fontWeight: 500 }}>Manipal Institute of Technology, Hyderabad</span>.
            I build intelligent systems — from computer vision pipelines to LLM-powered applications.
          </p>
          <p style={{
            fontFamily: 'Inter',
            fontSize: 'clamp(1rem, 1.3vw, 1.15rem)',
            color: '#888888',
            lineHeight: 1.8,
          }}>
            Passionate about turning cutting-edge research into real-world products. I thrive at the intersection
            of deep learning, software engineering, and product thinking.
          </p>

          {/* Tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
            {['Python', 'Deep Learning', 'LLMs', 'Computer Vision', 'MLOps'].map((tag) => (
              <span
                key={tag}
                style={{
                  fontFamily: 'Inter',
                  fontSize: '0.78rem',
                  color: '#00d4ff',
                  border: '1px solid rgba(0,212,255,0.25)',
                  borderRadius: '999px',
                  padding: '0.3rem 0.85rem',
                  background: 'rgba(0,212,255,0.06)',
                }}
              >
                {tag}
              </span>
            ))}
          </div>

          <a
            href="mailto:abhivasireddy13@gmail.com"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: '#FFFFFF',
              fontFamily: 'Inter',
              fontSize: '0.9rem',
              fontWeight: 500,
              textDecoration: 'none',
              marginTop: '0.5rem',
              padding: '0.75rem 1.75rem',
              borderRadius: '999px',
              border: '1.5px solid #00d4ff',
              background: 'transparent',
              transition: 'all 0.25s ease',
              width: 'fit-content',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = '#00d4ff'
              e.currentTarget.style.color = '#0a0a0f'
              e.currentTarget.style.boxShadow = '0 0 25px rgba(0,212,255,0.4)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = '#FFF'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            Download Resume →
          </a>
        </motion.div>
      </div>

      {/* Stats cards */}
      <motion.div
        variants={stagger}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '1px',
          border: '1px solid rgba(0,212,255,0.12)',
          borderRadius: '12px',
          overflow: 'hidden',
          background: 'rgba(0,212,255,0.08)',
        }}
      >
        {STATS.map(({ value, label }) => (
          <motion.div
            key={label}
            variants={fadeUp}
            style={{
              background: '#111827',
              padding: 'clamp(1.5rem, 3vw, 2.5rem)',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.4rem',
            }}
          >
            <span style={{
              fontFamily: 'Space Grotesk',
              fontSize: 'clamp(2rem, 3.5vw, 3rem)',
              fontWeight: 700,
              color: '#00d4ff',
              lineHeight: 1,
            }}>
              {value}
            </span>
            <span style={{
              fontFamily: 'Inter',
              fontSize: '0.875rem',
              color: '#888888',
              fontWeight: 400,
            }}>
              {label}
            </span>
          </motion.div>
        ))}
      </motion.div>
    </section>
  )
}
