import { useState } from 'react'
import { motion } from 'framer-motion'
import { Mail, Phone, ArrowRight } from 'lucide-react'

const GithubIcon = ({ size = 18, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color} xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2C6.477 2 2 6.477 2 12c0 4.419 2.865 8.166 6.839 9.489.5.09.682-.218.682-.484 0-.236-.009-.866-.013-1.699-2.782.603-3.369-1.342-3.369-1.342-.454-1.154-1.11-1.461-1.11-1.461-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.088 2.91.832.091-.647.349-1.086.635-1.337-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.03-2.682-.103-.253-.447-1.27.098-2.646 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836a9.59 9.59 0 0 1 2.504.337c1.909-1.294 2.747-1.025 2.747-1.025.546 1.376.202 2.394.1 2.646.64.699 1.026 1.591 1.026 2.682 0 3.841-2.337 4.687-4.565 4.935.359.309.678.917.678 1.852 0 1.335-.012 2.415-.012 2.741 0 .269.18.579.688.481C19.138 20.161 22 16.416 22 12c0-5.523-4.477-10-10-10z"/>
  </svg>
)

const LinkedinIcon = ({ size = 18, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color} xmlns="http://www.w3.org/2000/svg">
    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
  </svg>
)

const LINKS = [
  {
    Icon: ({ size, color }) => <Mail size={size} color={color} />,
    label: 'Email',
    value: 'abhivasireddy13@gmail.com',
    href: 'mailto:abhivasireddy13@gmail.com',
  },
  {
    Icon: LinkedinIcon,
    label: 'LinkedIn',
    value: 'linkedin.com/in/abhishek-sai-vasireddy',
    href: 'https://www.linkedin.com/in/abhishek-sai-vasireddy/',
  },
  {
    Icon: GithubIcon,
    label: 'GitHub',
    value: 'github.com/abhivasireddy13',
    href: 'https://github.com/abhivasireddy13',
  },
  {
    Icon: ({ size, color }) => <Phone size={size} color={color} />,
    label: 'Phone',
    value: '+91-9491886476',
    href: 'tel:+919491886476',
  },
]

function FuturisticGrid() {
  return (
    <svg
      style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', opacity: 0.07 }}
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
          <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#00d4ff" strokeWidth="0.5" />
        </pattern>
        <radialGradient id="fade" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="white" stopOpacity="1" />
          <stop offset="100%" stopColor="white" stopOpacity="0" />
        </radialGradient>
        <mask id="gridMask">
          <rect width="100%" height="100%" fill="url(#fade)" />
        </mask>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" mask="url(#gridMask)" />
    </svg>
  )
}

function ContactLink({ Icon, label, value, href }) {
  const [hov, setHov] = useState(false)
  return (
    <motion.a
      href={href}
      target={href.startsWith('http') ? '_blank' : undefined}
      rel="noopener noreferrer"
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      whileHover={{ x: 6 }}
      transition={{ duration: 0.2 }}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '1.25rem',
        padding: '1.25rem 1.75rem',
        background: hov ? '#111827' : 'rgba(17,24,39,0.5)',
        border: `1px solid ${hov ? 'rgba(0,212,255,0.4)' : 'rgba(0,212,255,0.1)'}`,
        borderRadius: '12px',
        textDecoration: 'none',
        transition: 'background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease',
        boxShadow: hov ? '0 0 25px rgba(0,212,255,0.08)' : 'none',
        cursor: 'pointer',
      }}
    >
      <div style={{
        width: '44px',
        height: '44px',
        borderRadius: '10px',
        background: hov ? 'rgba(0,212,255,0.12)' : 'rgba(0,212,255,0.05)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'background 0.25s ease',
        flexShrink: 0,
      }}>
        <Icon size={18} color={hov ? '#00d4ff' : '#475569'} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: 'Inter', fontSize: '0.72rem', color: '#475569', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.2rem' }}>
          {label}
        </div>
        <div style={{ fontFamily: 'Inter', fontSize: '0.9rem', color: hov ? '#e2e8f0' : '#94a3b8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', transition: 'color 0.2s ease' }}>
          {value}
        </div>
      </div>
      <ArrowRight size={16} color={hov ? '#00d4ff' : '#334155'} style={{ flexShrink: 0, transition: 'color 0.2s ease' }} />
    </motion.a>
  )
}

export default function Contact() {
  return (
    <section
      id="contact"
      style={{
        padding: 'clamp(5rem, 10vw, 9rem) clamp(1.5rem, 6vw, 7rem)',
        background: '#0a0a0f',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Futuristic grid background */}
      <FuturisticGrid />

      {/* Central glow */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: '700px',
        height: '700px',
        background: 'radial-gradient(circle, rgba(0,212,255,0.06) 0%, transparent 65%)',
        pointerEvents: 'none',
      }} />

      <div style={{ position: 'relative', zIndex: 1, maxWidth: '720px', margin: '0 auto', textAlign: 'center' }}>
        {/* Label */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          style={{ fontFamily: 'Inter', fontSize: '0.75rem', color: '#00d4ff', letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '1rem' }}
        >
          05 — Contact
        </motion.p>

        {/* Big heading */}
        <motion.h2
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
          style={{
            fontFamily: 'Space Grotesk',
            fontSize: 'clamp(2.5rem, 6vw, 5rem)',
            fontWeight: 700,
            letterSpacing: '-0.04em',
            color: '#e2e8f0',
            lineHeight: 1,
            marginBottom: '1.25rem',
          }}
        >
          Let's Build<br />
          <span style={{ color: '#00d4ff' }}>Something.</span>
        </motion.h2>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.1 }}
          style={{ fontFamily: 'Inter', fontSize: '1rem', color: '#64748b', lineHeight: 1.7, marginBottom: '3.5rem' }}
        >
          I'm actively looking for internship and full-time AI/ML roles. If you have an interesting problem to solve, I'd love to talk.
        </motion.p>

        {/* Links grid */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1rem',
            textAlign: 'left',
          }}
        >
          {LINKS.map((link) => (
            <ContactLink key={link.label} {...link} />
          ))}
        </motion.div>

        {/* CTA button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.35 }}
          style={{ marginTop: '2.5rem' }}
        >
          <SendButton href="mailto:abhivasireddy13@gmail.com" />
        </motion.div>
      </div>
    </section>
  )
}

function SendButton({ href }) {
  const [hov, setHov] = useState(false)
  return (
    <a
      href={href}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.75rem',
        fontFamily: 'Inter',
        fontWeight: 600,
        fontSize: '1rem',
        color: hov ? '#0a0a0f' : '#FFFFFF',
        background: hov ? '#00d4ff' : 'rgba(0,212,255,0.1)',
        border: '1.5px solid #00d4ff',
        padding: '1rem 2.5rem',
        borderRadius: '999px',
        textDecoration: 'none',
        transition: 'all 0.3s ease',
        boxShadow: hov ? '0 0 40px rgba(0,212,255,0.4)' : 'none',
      }}
    >
      <Mail size={18} />
      Send Me an Email
      <motion.span animate={{ x: hov ? 4 : 0 }} transition={{ duration: 0.2 }}>
        →
      </motion.span>
    </a>
  )
}
