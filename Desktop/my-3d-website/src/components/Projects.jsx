import { useRef, useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight, ExternalLink } from 'lucide-react'

// UPDATE project links when available
const PROJECTS = [
  {
    id: 1,
    name: 'AI Face Recognition System',
    description: 'Real-time face detection and recognition pipeline with 98% accuracy using deep metric learning and cosine similarity matching.',
    tech: ['OpenCV', 'DeepFace', 'Python', 'Flask'],
    link: 'https://github.com/abhivasireddy13',
    year: '2024',
    accent: 'rgba(255,69,0,0.12)',
  },
  {
    id: 2,
    name: 'LLM-Powered Chatbot',
    description: 'Production-ready conversational AI with multi-turn memory, RAG pipeline over private docs, and streaming response UI.',
    tech: ['LangChain', 'GPT-4', 'FastAPI', 'React'],
    link: 'https://github.com/abhivasireddy13/production-rag-pipeline',
    year: '2024',
    accent: 'rgba(255,100,50,0.1)',
  },
  {
    id: 3,
    name: 'Object Detection Pipeline',
    description: 'End-to-end YOLOv8 object detection with custom dataset training, Docker deployment, and real-time video inference.',
    tech: ['YOLOv8', 'PyTorch', 'Docker', 'OpenCV'],
    link: 'https://github.com/abhivasireddy13',
    year: '2024',
    accent: 'rgba(255,69,0,0.08)',
  },
  {
    id: 4,
    name: 'Procurement Analytics Dashboard',
    description: 'Interactive analytics dashboard for supply-chain procurement data with automated anomaly detection and trend forecasting.',
    tech: ['PostgreSQL', 'Metabase', 'Python', 'Pandas'],
    link: 'https://github.com/abhivasireddy13/ml-monitoring-drift-detection',
    year: '2023',
    accent: 'rgba(255,120,60,0.1)',
  },
  {
    id: 5,
    name: 'Certificate Generator',
    description: 'Bulk internship certificate automation system that generates personalized PDFs from templates with QR validation codes.',
    tech: ['ReportLab', 'Python', 'Pillow', 'PDF'],
    link: 'https://github.com/abhivasireddy13',
    year: '2023',
    accent: 'rgba(255,69,0,0.1)',
  },
]

function ProjectCard({ project, index }) {
  const cardRef = useRef(null)
  const [hov, setHov] = useState(false)

  const onMouseMove = useCallback((e) => {
    const rect = cardRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top)  / rect.height - 0.5
    cardRef.current.style.transform = `
      perspective(1200px)
      rotateY(${x * 12}deg)
      rotateX(${-y * 8}deg)
      translateZ(12px)
    `
  }, [])

  const onMouseLeave = useCallback(() => {
    cardRef.current.style.transform = `perspective(1200px) rotateY(0deg) rotateX(0deg) translateZ(0px)`
    setHov(false)
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, y: 60 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1], delay: index * 0.07 }}
    >
      <div
        ref={cardRef}
        onMouseMove={onMouseMove}
        onMouseLeave={onMouseLeave}
        onMouseEnter={() => setHov(true)}
        style={{
          background: '#111111',
          border: `1px solid ${hov ? 'rgba(255,69,0,0.35)' : '#1f1f1f'}`,
          borderRadius: '12px',
          padding: 'clamp(1.5rem, 3vw, 2.5rem)',
          transition: 'transform 0.15s ease, border-color 0.3s ease, box-shadow 0.3s ease',
          boxShadow: hov ? `0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,69,0,0.15), inset 0 0 0 1px rgba(255,69,0,0.05)` : 'none',
          willChange: 'transform',
          position: 'relative',
          overflow: 'hidden',
          cursor: 'pointer',
        }}
      >
        {/* Accent glow on hover */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: project.accent,
            opacity: hov ? 1 : 0,
            transition: 'opacity 0.4s ease',
            pointerEvents: 'none',
            borderRadius: '12px',
          }}
        />

        {/* Top row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', position: 'relative', zIndex: 1 }}>
          <span style={{
            fontFamily: 'Inter',
            fontSize: '0.72rem',
            color: '#FF4500',
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
          }}>
            {project.year}
          </span>
          <motion.div
            animate={{ rotate: hov ? 45 : 0, scale: hov ? 1.1 : 1 }}
            transition={{ duration: 0.25 }}
          >
            <ArrowUpRight size={18} color={hov ? '#FF4500' : '#444'} />
          </motion.div>
        </div>

        {/* Title */}
        <h3
          style={{
            fontFamily: 'Space Grotesk',
            fontSize: 'clamp(1.15rem, 2vw, 1.5rem)',
            fontWeight: 600,
            color: hov ? '#FFFFFF' : '#DDDDDD',
            letterSpacing: '-0.02em',
            marginBottom: '0.875rem',
            transition: 'color 0.2s ease',
            position: 'relative',
            zIndex: 1,
          }}
        >
          {project.name}
        </h3>

        {/* Description */}
        <p
          style={{
            fontFamily: 'Inter',
            fontSize: '0.9rem',
            color: '#666666',
            lineHeight: 1.7,
            marginBottom: '1.5rem',
            position: 'relative',
            zIndex: 1,
          }}
        >
          {project.description}
        </p>

        {/* Tech tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.5rem', position: 'relative', zIndex: 1 }}>
          {project.tech.map((t) => (
            <span
              key={t}
              style={{
                fontFamily: 'Inter',
                fontSize: '0.75rem',
                color: '#888888',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid #2a2a2a',
                borderRadius: '6px',
                padding: '0.25rem 0.65rem',
              }}
            >
              {t}
            </span>
          ))}
        </div>

        {/* CTA */}
        <a
          href={project.link}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            fontFamily: 'Inter',
            fontSize: '0.85rem',
            fontWeight: 500,
            color: hov ? '#FF4500' : '#555555',
            textDecoration: 'none',
            transition: 'color 0.2s ease',
            position: 'relative',
            zIndex: 1,
          }}
        >
          View Project <ExternalLink size={14} />
        </a>
      </div>
    </motion.div>
  )
}

export default function Projects() {
  return (
    <section
      id="projects"
      style={{
        padding: 'clamp(5rem, 10vw, 9rem) clamp(1.5rem, 6vw, 7rem)',
        background: '#080808',
        position: 'relative',
      }}
    >
      {/* Background accent */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: '400px',
        height: '400px',
        background: 'radial-gradient(circle, rgba(255,69,0,0.06) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      {/* Header */}
      <motion.p
        initial={{ opacity: 0, x: -20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        style={{ fontFamily: 'Inter', fontSize: '0.75rem', color: '#FF4500', letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '1rem' }}
      >
        03 — Projects
      </motion.p>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '3rem', flexWrap: 'wrap', gap: '1.5rem' }}>
        <motion.h2
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          style={{ fontFamily: 'Space Grotesk', fontSize: 'clamp(2rem, 4vw, 3.5rem)', fontWeight: 700, letterSpacing: '-0.03em', color: '#FFFFFF' }}
        >
          Selected<br />
          <span style={{ color: '#FF4500' }}>Work.</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          style={{ fontFamily: 'Inter', fontSize: '0.875rem', color: '#555', maxWidth: '260px', lineHeight: 1.6 }}
        >
          A curated selection of AI/ML projects spanning real-world deployments and research prototypes.
        </motion.p>
      </div>

      {/* Cards grid — 2 cols on desktop, 1 on mobile */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 400px), 1fr))',
          gap: '1.5rem',
        }}
      >
        {PROJECTS.map((project, i) => (
          <ProjectCard key={project.id} project={project} index={i} />
        ))}
      </div>

      {/* View all CTA */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, delay: 0.2 }}
        style={{ marginTop: '3rem', display: 'flex', justifyContent: 'center' }}
      >
        <a
          href="https://github.com/abhivasireddy13"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.6rem',
            fontFamily: 'Inter',
            fontSize: '0.9rem',
            fontWeight: 500,
            color: '#FFFFFF',
            border: '1.5px solid #FF4500',
            borderRadius: '999px',
            padding: '0.75rem 2rem',
            textDecoration: 'none',
            background: 'transparent',
            transition: 'background 0.25s ease, box-shadow 0.25s ease',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#FF4500'; e.currentTarget.style.boxShadow = '0 0 30px rgba(255,69,0,0.3)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.boxShadow = 'none' }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.477 2 2 6.477 2 12c0 4.419 2.865 8.166 6.839 9.489.5.09.682-.218.682-.484 0-.236-.009-.866-.013-1.699-2.782.603-3.369-1.342-3.369-1.342-.454-1.154-1.11-1.461-1.11-1.461-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.088 2.91.832.091-.647.349-1.086.635-1.337-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.03-2.682-.103-.253-.447-1.27.098-2.646 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836a9.59 9.59 0 0 1 2.504.337c1.909-1.294 2.747-1.025 2.747-1.025.546 1.376.202 2.394.1 2.646.64.699 1.026 1.591 1.026 2.682 0 3.841-2.337 4.687-4.565 4.935.359.309.678.917.678 1.852 0 1.335-.012 2.415-.012 2.741 0 .269.18.579.688.481C19.138 20.161 22 16.416 22 12c0-5.523-4.477-10-10-10z"/>
          </svg>
          View All on GitHub
        </a>
      </motion.div>
    </section>
  )
}
