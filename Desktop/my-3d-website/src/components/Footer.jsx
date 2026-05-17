import { useState } from 'react'
import { Mail } from 'lucide-react'

const GithubIcon = ({ size = 16, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <path d="M12 2C6.477 2 2 6.477 2 12c0 4.419 2.865 8.166 6.839 9.489.5.09.682-.218.682-.484 0-.236-.009-.866-.013-1.699-2.782.603-3.369-1.342-3.369-1.342-.454-1.154-1.11-1.461-1.11-1.461-.908-.62.069-.608.069-.608 1.003.07 1.531 1.03 1.531 1.03.892 1.529 2.341 1.088 2.91.832.091-.647.349-1.086.635-1.337-2.22-.253-4.555-1.11-4.555-4.943 0-1.091.39-1.984 1.03-2.682-.103-.253-.447-1.27.098-2.646 0 0 .84-.269 2.75 1.025A9.578 9.578 0 0 1 12 6.836a9.59 9.59 0 0 1 2.504.337c1.909-1.294 2.747-1.025 2.747-1.025.546 1.376.202 2.394.1 2.646.64.699 1.026 1.591 1.026 2.682 0 3.841-2.337 4.687-4.565 4.935.359.309.678.917.678 1.852 0 1.335-.012 2.415-.012 2.741 0 .269.18.579.688.481C19.138 20.161 22 16.416 22 12c0-5.523-4.477-10-10-10z"/>
  </svg>
)

const LinkedinIcon = ({ size = 16, color = 'currentColor' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
  </svg>
)

const SOCIALS = [
  { Icon: GithubIcon,   href: 'https://github.com/abhivasireddy13',                       label: 'GitHub'   },
  { Icon: LinkedinIcon, href: 'https://www.linkedin.com/in/abhishek-sai-vasireddy/',      label: 'LinkedIn' },
  { Icon: ({ size, color }) => <Mail size={size} color={color} />, href: 'mailto:abhivasireddy13@gmail.com', label: 'Email' },
]

function SocialIcon({ Icon, href, label }) {
  const [hov, setHov] = useState(false)
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        width: '38px',
        height: '38px',
        borderRadius: '50%',
        border: `1px solid ${hov ? 'rgba(0,212,255,0.5)' : 'rgba(0,212,255,0.12)'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: hov ? 'rgba(0,212,255,0.1)' : 'transparent',
        transition: 'all 0.25s ease',
        textDecoration: 'none',
        boxShadow: hov ? '0 0 15px rgba(0,212,255,0.3)' : 'none',
      }}
    >
      <Icon size={15} color={hov ? '#00d4ff' : '#475569'} />
    </a>
  )
}

export default function Footer() {
  return (
    <footer
      style={{
        borderTop: '1px solid rgba(0,212,255,0.1)',
        padding: '2rem clamp(1.5rem, 6vw, 7rem)',
        background: '#0a0a0f',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
      }}
    >
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        style={{ background: 'none', border: 'none', fontFamily: 'Space Grotesk', fontWeight: 700, fontSize: '1.1rem', color: '#e2e8f0', letterSpacing: '-0.02em', cursor: 'pointer' }}
      >
        VAS<span style={{ color: '#00d4ff' }}>.</span>
      </button>

      <p style={{ fontFamily: 'Inter', fontSize: '0.8rem', color: '#334155', textAlign: 'center' }}>
        Designed & Built by{' '}
        <span style={{ color: '#00d4ff' }}>Vasireddy Abhishek Sai</span>
        {' '}· 2026
      </p>

      <div style={{ display: 'flex', gap: '0.6rem' }}>
        {SOCIALS.map((s) => (
          <SocialIcon key={s.label} {...s} />
        ))}
      </div>
    </footer>
  )
}
