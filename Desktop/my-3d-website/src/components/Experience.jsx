import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'

const TIMELINE = [
  {
    type: 'work',
    role: 'AI/ML Intern',
    org: 'INCRESOL Software Services Pvt. Ltd.',
    period: 'Jan 2026 – Present',
    location: 'Hyderabad, India',
    bullets: [
      'Built a face-recognition attendance system using DeepFace + OpenCV with 98% accuracy.',
      'Designed REST APIs with FastAPI to serve inference endpoints for production use.',
      'Automated certificate generation pipeline reducing manual effort by 100%.',
      'Collaborated with senior engineers on PostgreSQL schema design and data pipelines.',
      'Built a real-time alerting system using Prometheus and Grafana that monitors pipeline health across 12+ workflows — reduced incident detection time from hours to under 5 minutes.',
      'Designed a hybrid search layer (BM25 + dense retrieval) using FAISS and ChromaDB on an internal knowledge base — improved document retrieval precision by ~30% for downstream LLM queries.',
      'Automated end-to-end report generation using LangGraph multi-agent workflows — chained data extraction, summarization, and formatting agents, cutting a 3-hour manual reporting process to under 10 minutes.',
    ],
    accent: '#00d4ff',
  },
  {
    type: 'work',
    role: 'Web Development Intern',
    org: 'BRC Web',
    period: 'May 2025 – Aug 2025',
    location: 'Remote',
    bullets: [
      'Containerized a churn prediction FastAPI service with Docker and deployed to AWS EC2 with auto-restart on failure; reduced deployment steps from ~12 to 2.',
      'Built a prompt caching and batching layer over the OpenAI API — cut token usage by ~35% and lowered monthly API costs across 3 client workflows.',
      'Developed a reusable Python library for client data ingestion (CSV, Excel, JSON) with schema validation and error logging; used across 5+ projects and reduced new data source onboarding from hours to under 30 minutes.',
    ],
    accent: '#7928ca',
  },
  {
    type: 'edu',
    role: 'B.Tech Computer Science & Engineering (AI & ML)',
    org: 'Manipal Institute of Technology, Hyderabad',
    period: '2022 – 2026',
    location: 'Hyderabad, India',
    bullets: [
      'Specialization in Artificial Intelligence and Machine Learning.',
      'Relevant coursework: Deep Learning, NLP, Computer Vision, Data Structures, Algorithms.',
      'Active member of the AI Research Club and Hackathon team.',
      'Multiple national hackathon participations.',
    ],
    accent: '#7928ca',
  },
]

function TimelineEntry({ item, index }) {
  const { ref, inView } = useInView({ threshold: 0.2, triggerOnce: true })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, x: 40 }}
      animate={inView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
      style={{
        display: 'grid',
        gridTemplateColumns: '1px 1fr',
        gap: '0 2.5rem',
        position: 'relative',
      }}
    >
      {/* Timeline node */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {/* Dot */}
        <motion.div
          initial={{ scale: 0 }}
          animate={inView ? { scale: 1 } : {}}
          transition={{ duration: 0.4, delay: 0.2 }}
          style={{
            width: '16px',
            height: '16px',
            borderRadius: '50%',
            background: item.accent,
            border: `3px solid #0a0a0f`,
            boxShadow: `0 0 20px ${item.accent}90, 0 0 40px ${item.accent}40`,
            flexShrink: 0,
            marginLeft: '-7.5px',
            zIndex: 2,
          }}
        />
        {/* Connecting line */}
        {index < TIMELINE.length - 1 && (
          <motion.div
            initial={{ scaleY: 0 }}
            animate={inView ? { scaleY: 1 } : {}}
            transition={{ duration: 0.8, delay: 0.4, ease: 'easeOut' }}
            style={{
              width: '1px',
              flex: 1,
              minHeight: '3rem',
              background: `linear-gradient(to bottom, ${item.accent}70, transparent)`,
              transformOrigin: 'top',
              marginTop: '4px',
            }}
          />
        )}
      </div>

      {/* Content card */}
      <div
        style={{
          background: '#111827',
          border: '1px solid rgba(0,212,255,0.1)',
          borderRadius: '12px',
          padding: 'clamp(1.25rem, 2.5vw, 2rem)',
          marginBottom: index < TIMELINE.length - 1 ? '2rem' : 0,
          transition: 'border-color 0.3s ease, box-shadow 0.3s ease',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = `${item.accent}50`
          e.currentTarget.style.boxShadow = `0 0 30px ${item.accent}10`
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = 'rgba(0,212,255,0.1)'
          e.currentTarget.style.boxShadow = 'none'
        }}
      >
        {/* Type badge */}
        <span style={{
          fontFamily: 'Inter',
          fontSize: '0.7rem',
          color: item.accent,
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
          marginBottom: '0.6rem',
          display: 'block',
        }}>
          {item.type === 'work' ? '● Work Experience' : '● Education'}
        </span>

        <h3 style={{
          fontFamily: 'Space Grotesk',
          fontSize: 'clamp(1.1rem, 1.8vw, 1.4rem)',
          fontWeight: 600,
          color: '#e2e8f0',
          letterSpacing: '-0.02em',
          marginBottom: '0.25rem',
        }}>
          {item.role}
        </h3>

        <p style={{ fontFamily: 'Inter', fontSize: '0.95rem', color: item.accent, fontWeight: 500, marginBottom: '0.25rem' }}>
          {item.org}
        </p>

        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
          <span style={{ fontFamily: 'Inter', fontSize: '0.8rem', color: '#475569' }}>{item.period}</span>
          <span style={{ fontFamily: 'Inter', fontSize: '0.8rem', color: '#334155' }}>·</span>
          <span style={{ fontFamily: 'Inter', fontSize: '0.8rem', color: '#475569' }}>{item.location}</span>
        </div>

        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
          {item.bullets.map((b, bi) => (
            <li
              key={bi}
              style={{ display: 'flex', gap: '0.65rem', alignItems: 'flex-start' }}
            >
              <span style={{ color: item.accent, marginTop: '0.35rem', flexShrink: 0, fontSize: '0.5rem' }}>▶</span>
              <span style={{ fontFamily: 'Inter', fontSize: '0.875rem', color: '#94a3b8', lineHeight: 1.65 }}>{b}</span>
            </li>
          ))}
        </ul>
      </div>
    </motion.div>
  )
}

export default function Experience() {
  return (
    <section
      id="experience"
      style={{
        padding: 'clamp(5rem, 10vw, 9rem) clamp(1.5rem, 6vw, 7rem)',
        background: '#0d1117',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background accent */}
      <div style={{
        position: 'absolute',
        top: '20%',
        right: '-100px',
        width: '450px',
        height: '450px',
        background: 'radial-gradient(circle, rgba(0,212,255,0.04) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* Header */}
      <motion.p
        initial={{ opacity: 0, x: -20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        style={{ fontFamily: 'Inter', fontSize: '0.75rem', color: '#00d4ff', letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '1rem' }}
      >
        04 — Experience
      </motion.p>

      <motion.h2
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        style={{ fontFamily: 'Space Grotesk', fontSize: 'clamp(2rem, 4vw, 3.5rem)', fontWeight: 700, letterSpacing: '-0.03em', color: '#e2e8f0', marginBottom: '4rem' }}
      >
        Where I've<br />
        <span style={{ color: '#00d4ff' }}>Been.</span>
      </motion.h2>

      {/* Timeline */}
      <div style={{ maxWidth: '760px' }}>
        {TIMELINE.map((item, i) => (
          <TimelineEntry key={i} item={item} index={i} />
        ))}
      </div>
    </section>
  )
}
