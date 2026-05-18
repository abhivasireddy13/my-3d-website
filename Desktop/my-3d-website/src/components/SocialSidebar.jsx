import { useState } from 'react'
import { FaGithub, FaLinkedinIn, FaInstagram } from 'react-icons/fa'

const SOCIALS = [
  { Icon: FaGithub,     href: 'https://github.com/abhivasireddy13',                   label: 'GitHub'    },
  { Icon: FaLinkedinIn, href: 'https://www.linkedin.com/in/abhishek-sai-vasireddy/',  label: 'LinkedIn'  },
  { Icon: FaInstagram,  href: 'https://www.instagram.com/abhi.vasireddy13/',          label: 'Instagram' },
]

function SocialBtn({ Icon, href, label }) {
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
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '38px',
        height: '38px',
        borderRadius: '8px',
        color: hov ? '#00d4ff' : '#6b7280',
        transform: hov ? 'scale(1.2)' : 'scale(1)',
        transition: 'all 0.25s ease',
        textDecoration: 'none',
        filter: hov ? 'drop-shadow(0 0 10px rgba(0,212,255,0.75))' : 'none',
      }}
    >
      <Icon size={22} />
    </a>
  )
}

export default function SocialSidebar() {
  return (
    <div
      style={{
        position: 'fixed',
        left: '1.5rem',
        top: '50%',
        transform: 'translateY(-50%)',
        zIndex: 100,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '0.75rem',
      }}
      className="social-sidebar"
    >
      {SOCIALS.map((s) => (
        <SocialBtn key={s.label} {...s} />
      ))}
      <div
        style={{
          width: '1px',
          height: '80px',
          background: 'linear-gradient(to bottom, rgba(0,212,255,0.4), transparent)',
          marginTop: '0.5rem',
        }}
      />
      <style>{`
        @media (max-width: 768px) { .social-sidebar { display: none; } }
      `}</style>
    </div>
  )
}
