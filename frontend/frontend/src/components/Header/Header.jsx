import { useState, useEffect } from 'react'
import { Link, NavLink } from 'react-router-dom'
import './Header.css'

export default function Header() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [menuOpen])

  return (
    <header className={`site-header${scrolled ? ' site-header--scrolled' : ''}`}>
      {/* Institutional Utility Bar */}
      <div className="utility-bar" role="banner">
        <div className="container utility-bar__inner">
          <span className="utility-bar__brand">
            PULLI — Computational Study of Traditional Kolam Patterns
          </span>
          <nav className="utility-bar__links" aria-label="Utility navigation">
            <a href="#main-content" className="utility-bar__link utility-bar__skip">
              Skip to content
            </a>
            <span className="utility-bar__link">Accessibility</span>
            <span className="utility-bar__link">EN</span>
            <Link to="/about" className="utility-bar__link">Contact</Link>
          </nav>
        </div>
      </div>

      {/* Main navigation */}
      <div className="main-nav">
        <div className="container main-nav__inner">
          {/* Logo / wordmark */}
          <Link to="/" className="wordmark" aria-label="PULLI Home">
            <div className="wordmark__mark" aria-hidden="true">
              <svg viewBox="0 0 42 28" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="7" cy="7" r="2.2" fill="currentColor"/>
                <circle cx="21" cy="7" r="2.2" fill="currentColor"/>
                <circle cx="35" cy="7" r="2.2" fill="currentColor"/>
                <circle cx="14" cy="14" r="2.2" fill="currentColor"/>
                <circle cx="28" cy="14" r="2.2" fill="currentColor"/>
                <circle cx="7" cy="21" r="2.2" fill="currentColor"/>
                <circle cx="21" cy="21" r="2.2" fill="currentColor"/>
                <circle cx="35" cy="21" r="2.2" fill="currentColor"/>
                <line x1="7" y1="7" x2="14" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4"/>
                <line x1="21" y1="7" x2="14" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4"/>
                <line x1="21" y1="7" x2="28" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4"/>
                <line x1="35" y1="7" x2="28" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4"/>
                <line x1="14" y1="14" x2="7" y2="21" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4"/>
                <line x1="14" y1="14" x2="21" y2="21" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4"/>
                <line x1="28" y1="14" x2="21" y2="21" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4"/>
                <line x1="28" y1="14" x2="35" y2="21" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.4"/>
              </svg>
            </div>
            <div className="wordmark__text">
              <span className="wordmark__name">PULLI</span>
              <span className="wordmark__subtitle">Computational Understanding of One-Stroke Dotted Kolam Patterns</span>
            </div>
          </Link>

          {/* Desktop nav links */}
          <nav className="desktop-nav" aria-label="Main navigation">
            <NavLink to="/" end className={({ isActive }) => isActive ? 'desktop-nav__link desktop-nav__link--active' : 'desktop-nav__link'}>
              Home
            </NavLink>
            <NavLink to="/project" className={({ isActive }) => isActive ? 'desktop-nav__link desktop-nav__link--active' : 'desktop-nav__link'}>
              Project
            </NavLink>
            <NavLink to="/how-it-works" className={({ isActive }) => isActive ? 'desktop-nav__link desktop-nav__link--active' : 'desktop-nav__link'}>
              How It Works
            </NavLink>
            <NavLink to="/explore" className={({ isActive }) => isActive ? 'desktop-nav__link desktop-nav__link--active' : 'desktop-nav__link'}>
              Explore
            </NavLink>
            <NavLink to="/technology" className={({ isActive }) => isActive ? 'desktop-nav__link desktop-nav__link--active' : 'desktop-nav__link'}>
              Technology
            </NavLink>
            <NavLink to="/impact" className={({ isActive }) => isActive ? 'desktop-nav__link desktop-nav__link--active' : 'desktop-nav__link'}>
              Impact
            </NavLink>
            <NavLink to="/about" className={({ isActive }) => isActive ? 'desktop-nav__link desktop-nav__link--active' : 'desktop-nav__link'}>
              About
            </NavLink>
          </nav>

          {/* Mobile hamburger */}
          <button
            className={`hamburger${menuOpen ? ' hamburger--open' : ''}`}
            onClick={() => setMenuOpen(v => !v)}
            aria-expanded={menuOpen}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          >
            <span className="hamburger__bar" />
            <span className="hamburger__bar" />
            <span className="hamburger__bar" />
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {menuOpen && (
        <div className="mobile-menu" role="dialog" aria-modal="true" aria-label="Site navigation">
          <nav className="mobile-menu__nav">
            <NavLink to="/" end onClick={() => setMenuOpen(false)} className="mobile-menu__link">Home</NavLink>
            <NavLink to="/project" onClick={() => setMenuOpen(false)} className="mobile-menu__link">Project</NavLink>
            <NavLink to="/how-it-works" onClick={() => setMenuOpen(false)} className="mobile-menu__link">How It Works</NavLink>
            <NavLink to="/explore" onClick={() => setMenuOpen(false)} className="mobile-menu__link">Explore</NavLink>
            <NavLink to="/technology" onClick={() => setMenuOpen(false)} className="mobile-menu__link">Technology</NavLink>
            <NavLink to="/impact" onClick={() => setMenuOpen(false)} className="mobile-menu__link">Impact</NavLink>
            <NavLink to="/about" onClick={() => setMenuOpen(false)} className="mobile-menu__link">About</NavLink>
          </nav>
        </div>
      )}
    </header>
  )
}
