import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const NAV_LINKS = ['About', 'Skills', 'Projects', 'Experience', 'Contact']
const ACCENT = '#00e5ff'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const scrollTo = (id) => {
    document.getElementById(id.toLowerCase())?.scrollIntoView({ behavior: 'smooth' })
    setMenuOpen(false)
  }

  return (
    <motion.nav
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 200,
        padding: '0 clamp(1.5rem, 5vw, 4rem)',
        height: '64px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: scrolled ? 'rgba(10,10,15,0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(16px)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(0,229,255,0.08)' : 'none',
        transition: 'all 0.35s ease',
      }}
    >
      {/* AV Logo */}
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          fontFamily: 'Space Grotesk',
          fontSize: '1.35rem',
          fontWeight: 800,
          letterSpacing: '-0.02em',
          color: '#fff',
          padding: 0,
        }}
      >
        AV<span style={{ color: ACCENT }}>.</span>
      </button>

      {/* Desktop nav */}
      <div className="nav-links" style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        {NAV_LINKS.map((link) => (
          <NavLink key={link} onClick={() => scrollTo(link)}>{link}</NavLink>
        ))}
        <a
          href={`${import.meta.env.BASE_URL}Abhi_Vasireddy.pdf`}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontFamily: 'Inter',
            fontSize: '0.82rem',
            fontWeight: 600,
            letterSpacing: '0.06em',
            color: '#0a0a0f',
            background: ACCENT,
            padding: '0.5rem 1.4rem',
            borderRadius: '999px',
            textDecoration: 'none',
            transition: 'box-shadow 0.25s ease',
          }}
          onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 0 22px rgba(0,229,255,0.5)` }}
          onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none' }}
        >
          Resume
        </a>
      </div>

      {/* Mobile hamburger */}
      <button
        className="nav-hamburger"
        onClick={() => setMenuOpen(o => !o)}
        style={{
          display: 'none',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: '0.5rem',
          flexDirection: 'column',
          gap: '5px',
        }}
      >
        {[0, 1, 2].map(i => (
          <span key={i} style={{
            display: 'block',
            width: '22px',
            height: '2px',
            background: menuOpen ? ACCENT : '#888',
            borderRadius: '2px',
            transition: 'all 0.2s',
            transform: menuOpen && i === 0 ? 'rotate(45deg) translate(5px, 5px)'
              : menuOpen && i === 2 ? 'rotate(-45deg) translate(5px, -5px)'
              : menuOpen && i === 1 ? 'scaleX(0)' : 'none',
          }} />
        ))}
      </button>

      {/* Mobile drawer */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.25 }}
            style={{
              position: 'absolute',
              top: '64px',
              left: 0,
              right: 0,
              background: 'rgba(10,10,15,0.98)',
              borderBottom: `1px solid rgba(0,229,255,0.12)`,
              padding: '1.5rem 2rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}
          >
            {NAV_LINKS.map(link => (
              <button
                key={link}
                onClick={() => scrollTo(link)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontFamily: 'Inter',
                  fontSize: '1rem',
                  fontWeight: 500,
                  color: '#ccc',
                  textAlign: 'left',
                  padding: 0,
                }}
              >
                {link}
              </button>
            ))}
            <a
              href={`${import.meta.env.BASE_URL}Abhi_Vasireddy.pdf`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: ACCENT, fontFamily: 'Inter', fontSize: '1rem', fontWeight: 600, textDecoration: 'none', width: 'fit-content' }}
            >
              Resume ↓
            </a>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        @media (max-width: 768px) {
          .nav-links { display: none !important; }
          .nav-hamburger { display: flex !important; }
        }
      `}</style>
    </motion.nav>
  )
}

function NavLink({ onClick, children }) {
  const [hov, setHov] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        fontFamily: 'Inter',
        fontSize: '0.82rem',
        fontWeight: 500,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        color: hov ? ACCENT : '#888',
        padding: '0.25rem 0',
        transition: 'color 0.2s ease',
        position: 'relative',
      }}
    >
      {children}
      <span style={{
        position: 'absolute',
        bottom: '-2px',
        left: 0,
        width: hov ? '100%' : '0%',
        height: '1px',
        background: ACCENT,
        transition: 'width 0.25s ease',
      }} />
    </button>
  )
}
