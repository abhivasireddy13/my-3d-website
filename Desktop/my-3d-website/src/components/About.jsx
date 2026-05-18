import { motion } from 'framer-motion'
import SplineScene from './SplineScene'

const ACCENT = '#00e5ff'

const STATS = [
  { value: '5+',    label: 'Projects Shipped' },
  { value: '2',     label: 'Internships' },
  { value: '2026',  label: 'Graduating' },
  { value: 'AI/ML', label: 'Specialisation' },
]

const CERTS = [
  { title: 'Google AI Essentials & Generative AI',           issuer: 'Google / Coursera',           date: 'Mar 2026' },
  { title: 'Machine Learning with Python',                    issuer: 'IBM / Coursera',              date: 'Apr 2026' },
  { title: 'Google Data Analytics Professional Certificate',  issuer: 'Google / Coursera',           date: 'Nov 2025' },
  { title: 'Deep Learning Specialization',                    issuer: 'DeepLearning.AI — Andrew Ng', date: 'Feb 2025' },
  { title: 'Machine Learning Specialization',                 issuer: 'DeepLearning.AI — Andrew Ng', date: 'Aug 2024' },
]

const fadeUp = {
  hidden: { opacity: 0, y: 48 },
  show:   { opacity: 1, y: 0, transition: { duration: 0.75, ease: [0.22, 1, 0.36, 1] } },
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
        background: '#0a0a0f',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* — TOP: ABOUT ME hero block ————————————————————————— */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          minHeight: '85vh',
          alignItems: 'stretch',
        }}
      >
        {/* Left: Spline character */}
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          style={{
            position: 'relative',
            minHeight: '480px',
            background: 'rgba(0,229,255,0.02)',
            borderRight: '1px solid rgba(0,229,255,0.07)',
            overflow: 'hidden',
          }}
        >
          <SplineScene style={{ minHeight: '480px' }} />
          {/* Subtle gradient overlay to blend into right panel */}
          <div style={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: '80px',
            height: '100%',
            background: 'linear-gradient(to right, transparent, #0a0a0f)',
            pointerEvents: 'none',
          }} />
        </motion.div>

        {/* Right: text */}
        <motion.div
          initial={{ opacity: 0, x: 40 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
          style={{
            padding: 'clamp(3rem, 7vw, 7rem) clamp(2rem, 6vw, 6rem)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            gap: '1.75rem',
          }}
        >
          {/* Label */}
          <p style={{
            fontFamily: 'Inter',
            fontSize: '0.75rem',
            color: ACCENT,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
          }}>
            01 — About
          </p>

          {/* Heading */}
          <h2 style={{
            fontFamily: 'Space Grotesk',
            fontSize: 'clamp(2.2rem, 5vw, 4.5rem)',
            fontWeight: 800,
            letterSpacing: '-0.04em',
            lineHeight: 0.95,
            color: '#fff',
            margin: 0,
          }}>
            ABOUT<br />
            <span style={{ color: ACCENT }}>ME.</span>
          </h2>

          {/* Bio */}
          <p style={{
            fontFamily: 'Inter',
            fontSize: 'clamp(0.95rem, 1.3vw, 1.1rem)',
            color: '#aaa',
            lineHeight: 1.85,
            maxWidth: '520px',
          }}>
            Final-year B.Tech student in Computer Science (AI &amp; ML) at{' '}
            <span style={{ color: '#e2e8f0', fontWeight: 500 }}>Manipal Institute of Technology</span>,
            graduating 2026. I specialise in end-to-end ML systems — from LLM fine-tuning
            and RAG pipelines to production MLOps infrastructure.
          </p>

          <p style={{
            fontFamily: 'Inter',
            fontSize: 'clamp(0.95rem, 1.3vw, 1.1rem)',
            color: '#666',
            lineHeight: 1.85,
            maxWidth: '520px',
          }}>
            I've shipped projects across medical imaging, NLP, generative AI, and
            real-time model monitoring — with hands-on internship experience on
            Azure OpenAI, AWS Bedrock, and GCP Vertex AI.
          </p>

          {/* Tags */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
            {['LLMs & GenAI', 'RAG Pipelines', 'MLOps', 'Computer Vision', 'Data Engineering'].map(tag => (
              <span key={tag} style={{
                fontFamily: 'Inter',
                fontSize: '0.78rem',
                color: ACCENT,
                border: `1px solid rgba(0,229,255,0.25)`,
                borderRadius: '999px',
                padding: '0.3rem 0.85rem',
                background: 'rgba(0,229,255,0.06)',
              }}>
                {tag}
              </span>
            ))}
          </div>

          {/* Resume download */}
          <a
            href={`${import.meta.env.BASE_URL}Abhi_Vasireddy.pdf`}
            download
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.5rem',
              color: '#fff',
              fontFamily: 'Inter',
              fontSize: '0.9rem',
              fontWeight: 500,
              textDecoration: 'none',
              padding: '0.75rem 1.75rem',
              borderRadius: '999px',
              border: `1.5px solid ${ACCENT}`,
              background: 'transparent',
              transition: 'all 0.25s ease',
              width: 'fit-content',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = ACCENT
              e.currentTarget.style.color = '#0a0a0f'
              e.currentTarget.style.boxShadow = '0 0 25px rgba(0,229,255,0.4)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = '#fff'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            Download Resume ↓
          </a>
        </motion.div>
      </div>

      {/* — STATS ——————————————————————————————————————————— */}
      <motion.div
        variants={stagger}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '1px',
          background: 'rgba(0,229,255,0.08)',
          borderTop: '1px solid rgba(0,229,255,0.1)',
          borderBottom: '1px solid rgba(0,229,255,0.1)',
        }}
      >
        {STATS.map(({ value, label }) => (
          <motion.div key={label} variants={fadeUp} style={{
            background: '#0a0a0f',
            padding: 'clamp(1.5rem, 3vw, 2.5rem)',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.4rem',
          }}>
            <span style={{ fontFamily: 'Space Grotesk', fontSize: 'clamp(2rem, 3.5vw, 3rem)', fontWeight: 700, color: ACCENT, lineHeight: 1 }}>
              {value}
            </span>
            <span style={{ fontFamily: 'Inter', fontSize: '0.875rem', color: '#555', fontWeight: 400 }}>
              {label}
            </span>
          </motion.div>
        ))}
      </motion.div>

      {/* — EDUCATION ————————————————————————————————————— */}
      <div style={{ padding: 'clamp(3rem, 7vw, 6rem) clamp(1.5rem, 6vw, 7rem)' }}>
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
          style={{ marginBottom: '4rem' }}
        >
          <p style={{ fontFamily: 'Inter', fontSize: '0.75rem', color: ACCENT, letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '1.5rem' }}>
            Education
          </p>
          <div style={{
            background: '#0d1117',
            border: '1px solid rgba(0,229,255,0.1)',
            borderRadius: '12px',
            padding: 'clamp(1.5rem, 3vw, 2rem)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            flexWrap: 'wrap',
            gap: '1rem',
          }}>
            <div>
              <p style={{ fontFamily: 'Space Grotesk', fontSize: '1.1rem', fontWeight: 600, color: '#e2e8f0', marginBottom: '0.3rem' }}>
                B.Tech — Computer Science Engineering (AI &amp; ML)
              </p>
              <p style={{ fontFamily: 'Inter', fontSize: '0.95rem', color: ACCENT, fontWeight: 500, marginBottom: '0.25rem' }}>
                Manipal Institute of Technology, Manipal
              </p>
              <p style={{ fontFamily: 'Inter', fontSize: '0.8rem', color: '#475569' }}>Hyderabad, India</p>
            </div>
            <span style={{
              fontFamily: 'Inter',
              fontSize: '0.8rem',
              color: '#475569',
              background: 'rgba(0,229,255,0.06)',
              border: '1px solid rgba(0,229,255,0.15)',
              borderRadius: '999px',
              padding: '0.3rem 1rem',
              whiteSpace: 'nowrap',
            }}>
              2021 – 2026
            </span>
          </div>
        </motion.div>

        {/* Certifications */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          <p style={{ fontFamily: 'Inter', fontSize: '0.75rem', color: ACCENT, letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '1.5rem' }}>
            Certifications
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 340px), 1fr))', gap: '1rem' }}>
            {CERTS.map((c, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.07 }}
                style={{
                  background: '#0d1117',
                  border: '1px solid rgba(0,229,255,0.08)',
                  borderRadius: '10px',
                  padding: '1rem 1.25rem',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.3rem',
                }}
              >
                <p style={{ fontFamily: 'Inter', fontSize: '0.875rem', fontWeight: 500, color: '#e2e8f0', lineHeight: 1.4 }}>{c.title}</p>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{ fontFamily: 'Inter', fontSize: '0.75rem', color: '#475569' }}>{c.issuer}</span>
                  <span style={{ fontFamily: 'Inter', fontSize: '0.72rem', color: ACCENT, background: 'rgba(0,229,255,0.06)', border: '1px solid rgba(0,229,255,0.15)', borderRadius: '999px', padding: '0.15rem 0.65rem' }}>{c.date}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
