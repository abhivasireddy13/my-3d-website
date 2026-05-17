import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Menu, X } from 'lucide-react'

const NAV_LINKS = ['About', 'Skills', 'Projects', 'Experience', 'Contact']

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 60)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const scrollTo = (id) => {
    const el = document.getElementById(id.toLowerCase())
    if (el) el.scrollIntoView({ behavior: 'smooth' })
    setMobileOpen(false)
  }

  return (
    <motion.nav
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 200,
        padding: '0 clamp(1.5rem, 5vw, 4rem)',
        height: '70px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        transition: 'background 0.4s ease, backdrop-filter 0.4s ease, border-color 0.4s ease',
        background: scrolled ? 'rgba(10,10,15,0.9)' : 'transparent',
        backdropFilter: scrolled ? 'blur(24px) saturate(180%)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(0,212,255,0.12)' : '1px solid transparent',
      }}
    >
      {/* Logo */}
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        style={{
          background: 'none',
          border: 'none',
          color: '#FFFFFF',
          fontFamily: 'Space Grotesk',
          fontWeight: 700,
          fontSize: '1.25rem',
          letterSpacing: '-0.03em',
          cursor: 'pointer',
        }}
      >
        VAS<span style={{ color: '#00d4ff' }}>.</span>
      </button>

      {/* Desktop Links */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '2.5rem',
        }}
        className="hidden md:flex"
      >
        {NAV_LINKS.map((link) => (
          <NavLink key={link} onClick={() => scrollTo(link)}>
            {link}
          </NavLink>
        ))}
        <PillButton onClick={() => scrollTo('Contact')}>
          Hire Me
        </PillButton>
      </div>

      {/* Mobile toggle */}
      <button
        className="md:hidden"
        onClick={() => setMobileOpen((v) => !v)}
        style={{
          background: 'none',
          border: 'none',
          color: '#FFFFFF',
          padding: '0.25rem',
          cursor: 'pointer',
        }}
      >
        {mobileOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.25 }}
            style={{
              position: 'absolute',
              top: '70px',
              left: 0,
              right: 0,
              background: 'rgba(10,10,15,0.97)',
              backdropFilter: 'blur(24px)',
              borderBottom: '1px solid rgba(0,212,255,0.12)',
              padding: '1.5rem clamp(1.5rem, 5vw, 4rem)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}
          >
            {NAV_LINKS.map((link) => (
              <button
                key={link}
                onClick={() => scrollTo(link)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#888888',
                  fontFamily: 'Inter',
                  fontSize: '1rem',
                  fontWeight: 500,
                  textAlign: 'left',
                  cursor: 'pointer',
                }}
              >
                {link}
              </button>
            ))}
            <PillButton onClick={() => scrollTo('Contact')}>Hire Me</PillButton>
          </motion.div>
        )}
      </AnimatePresence>
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
        color: hov ? '#00d4ff' : '#888888',
        fontFamily: 'Inter',
        fontSize: '0.875rem',
        fontWeight: 500,
        transition: 'color 0.2s ease',
        position: 'relative',
        cursor: 'pointer',
      }}
    >
      {children}
      <span
        style={{
          position: 'absolute',
          bottom: '-3px',
          left: 0,
          width: hov ? '100%' : '0%',
          height: '1px',
          background: '#00d4ff',
          transition: 'width 0.25s ease',
        }}
      />
    </button>
  )
}

function PillButton({ onClick, children }) {
  const [hov, setHov] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        background: hov ? '#00d4ff' : 'transparent',
        border: '1.5px solid #00d4ff',
        color: hov ? '#0a0a0f' : '#00d4ff',
        fontFamily: 'Inter',
        fontSize: '0.875rem',
        fontWeight: hov ? 700 : 500,
        padding: '0.5rem 1.5rem',
        borderRadius: '999px',
        transition: 'all 0.25s ease',
        whiteSpace: 'nowrap',
        cursor: 'pointer',
        boxShadow: hov ? '0 0 20px rgba(0,212,255,0.4)' : 'none',
      }}
    >
      {children}
    </button>
  )
}
