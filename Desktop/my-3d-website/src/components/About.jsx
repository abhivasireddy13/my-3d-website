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

export default function About() {
  return (
    <section
      id="about"
      style={{
        padding: 'clamp(5rem, 10vw, 9rem) clamp(1.5rem, 6vw, 7rem)',
        background: '#080808',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Accent corner glow */}
      <div style={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: '500px',
        height: '500px',
        background: 'radial-gradient(circle, rgba(255,69,0,0.07) 0%, transparent 70%)',
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
          color: '#FF4500',
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
          color: '#FFFFFF',
          marginBottom: '4rem',
        }}
      >
        The Engineer<br />
        <span style={{ color: '#FF4500' }}>Behind the Code.</span>
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
              border: '1px solid #1f1f1f',
              overflow: 'hidden',
              position: 'relative',
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
            <span style={{ color: '#FF4500', fontWeight: 500 }}>Manipal Institute of Technology, Hyderabad</span>.
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
                  color: '#FF4500',
                  border: '1px solid rgba(255,69,0,0.3)',
                  borderRadius: '999px',
                  padding: '0.3rem 0.85rem',
                  background: 'rgba(255,69,0,0.06)',
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
              border: '1.5px solid #FF4500',
              background: 'transparent',
              transition: 'all 0.25s ease',
              width: 'fit-content',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#FF4500'; e.currentTarget.style.color = '#FFF' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#FFF' }}
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
          border: '1px solid #1f1f1f',
          borderRadius: '12px',
          overflow: 'hidden',
          background: '#1f1f1f',
        }}
      >
        {STATS.map(({ value, label }) => (
          <motion.div
            key={label}
            variants={fadeUp}
            style={{
              background: '#111111',
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
              color: '#FF4500',
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
