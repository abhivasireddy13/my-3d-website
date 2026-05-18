import { useRef, useCallback, useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight, ExternalLink, Terminal } from 'lucide-react'

const PROJECTS = [
  {
    id: 1,
    name: 'Production RAG Pipeline',
    description: 'Production-grade RAG pipeline with hybrid BM25 + dense vector search, Cohere re-ranking, streaming responses, citation tracking, and a RAGAS evaluation harness — p95 query latency under 800 ms on a 100K+ document corpus.',
    tech: ['Python', 'LangChain', 'FAISS', 'OpenAI', 'Cohere', 'FastAPI', 'RAGAS', 'Docker'],
    link: 'https://github.com/abhivasireddy13/production-rag-pipeline',
    year: '2025',
  },
  {
    id: 2,
    name: 'ML Monitoring & Drift Detection System',
    description: 'Production ML observability stack monitoring 10+ models for performance degradation and feature drift — MTTD reduced from days to under 15 minutes.',
    tech: ['Python', 'Prometheus', 'Grafana', 'MLflow', 'Evidently AI', 'Docker', 'GitHub Actions'],
    link: 'https://github.com/abhivasireddy13/ml-monitoring-drift-detection',
    year: '2025',
  },
  {
    id: 3,
    name: 'AI Agents for Medical Diagnostics',
    description: 'Multi-agent LLM system with specialised agents for symptom intake, differential diagnosis, and triage — 91% top-3 diagnostic agreement on 200+ clinical cases.',
    tech: ['Python', 'LangChain', 'OpenAI', 'Multi-Agent', 'Function Calling', 'Guardrails'],
    link: 'https://github.com/abhivasireddy13/AI-Agents-for-Medical-Diagnostics',
    year: '2025',
  },
  {
    id: 4,
    name: 'Multimodal Document Intelligence',
    description: 'Vision-language system combining PaddleOCR with LLaVA-style multimodal models — 70% reduction in manual review effort on a 5,000-document benchmark.',
    tech: ['Python', 'PaddleOCR', 'LLaVA', 'ChromaDB', 'Sentence Transformers', 'FastAPI'],
    link: 'https://github.com/abhivasireddy13/multimodal-document-intelligence',
    year: '2025',
  },
  {
    id: 5,
    name: 'Amazon Customer Reviews — NLP Benchmark',
    description: 'Sentiment analysis API benchmarking VADER, TF-IDF + Logistic Regression, and DistilBERT on Amazon reviews — FastAPI backend + Streamlit frontend.',
    tech: ['Python', 'DistilBERT', 'VADER', 'TF-IDF', 'FastAPI', 'Streamlit', 'HuggingFace'],
    link: 'https://github.com/abhivasireddy13/Amazon-Customer-Reviews',
    year: '2024',
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
          background: '#111827',
          border: `1px solid ${hov ? 'rgba(0,212,255,0.45)' : 'rgba(0,212,255,0.1)'}`,
          borderRadius: '12px',
          padding: 'clamp(1.5rem, 3vw, 2.5rem)',
          transition: 'transform 0.15s ease, border-color 0.3s ease, box-shadow 0.3s ease',
          boxShadow: hov
            ? '0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(0,212,255,0.15), 0 0 40px rgba(0,212,255,0.08)'
            : 'none',
          willChange: 'transform',
          position: 'relative',
          overflow: 'hidden',
          cursor: 'pointer',
        }}
      >
        {/* Cyan glow on hover */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(0,212,255,0.04)',
            opacity: hov ? 1 : 0,
            transition: 'opacity 0.4s ease',
            pointerEvents: 'none',
            borderRadius: '12px',
          }}
        />

        {/* Top row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Terminal size={14} color={hov ? '#00d4ff' : '#334155'} style={{ transition: 'color 0.2s' }} />
            <span style={{
              fontFamily: 'Inter',
              fontSize: '0.72rem',
              color: hov ? '#00d4ff' : '#475569',
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              transition: 'color 0.2s',
            }}>
              {project.year}
            </span>
          </div>
          <motion.div
            animate={{ rotate: hov ? 45 : 0, scale: hov ? 1.1 : 1 }}
            transition={{ duration: 0.25 }}
          >
            <ArrowUpRight size={18} color={hov ? '#00d4ff' : '#334155'} />
          </motion.div>
        </div>

        {/* Title */}
        <h3
          style={{
            fontFamily: 'Space Grotesk',
            fontSize: 'clamp(1.15rem, 2vw, 1.5rem)',
            fontWeight: 600,
            color: hov ? '#FFFFFF' : '#e2e8f0',
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
            color: '#64748b',
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
                color: hov ? '#94a3b8' : '#64748b',
                background: hov ? 'rgba(0,212,255,0.06)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${hov ? 'rgba(0,212,255,0.2)' : '#1e293b'}`,
                borderRadius: '6px',
                padding: '0.25rem 0.65rem',
                transition: 'all 0.2s ease',
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
            color: hov ? '#00d4ff' : '#475569',
            textDecoration: 'none',
            transition: 'color 0.2s ease',
            position: 'relative',
            zIndex: 1,
          }}
        >
          View on GitHub <ExternalLink size={14} />
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
        background: '#0a0a0f',
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
        background: 'radial-gradient(circle, rgba(0,212,255,0.05) 0%, transparent 70%)',
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
        03 — Projects
      </motion.p>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: '3rem', flexWrap: 'wrap', gap: '1.5rem' }}>
        <motion.h2
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          style={{ fontFamily: 'Space Grotesk', fontSize: 'clamp(2rem, 4vw, 3.5rem)', fontWeight: 700, letterSpacing: '-0.03em', color: '#e2e8f0' }}
        >
          Selected<br />
          <span style={{ color: '#00d4ff' }}>Work.</span>
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

      {/* Cards grid */}
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
            border: '1.5px solid #00d4ff',
            borderRadius: '999px',
            padding: '0.75rem 2rem',
            textDecoration: 'none',
            background: 'transparent',
            transition: 'background 0.25s ease, box-shadow 0.25s ease, color 0.25s ease',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = '#00d4ff'
            e.currentTarget.style.color = '#0a0a0f'
            e.currentTarget.style.boxShadow = '0 0 30px rgba(0,212,255,0.4)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'transparent'
            e.currentTarget.style.color = '#FFF'
            e.currentTarget.style.boxShadow = 'none'
          }}
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
