import { useState, useRef, useEffect } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { ChevronDown, Sun, Moon, User } from 'lucide-react'
import { useLanguage } from '../../context/LanguageContext'
import { LANGUAGES } from '../../i18n/index'
import './Header.css'

export default function Header() {
  const { lang, setLanguage, t } = useLanguage()
  const [langOpen, setLangOpen] = useState(false)
  const dropdownRef = useRef(null)

  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem('pulli-theme')
      if (saved === 'dark') {
        document.documentElement.classList.add('dark-theme')
        return 'dark'
      }
    } catch {
      /* ignore */
    }
    document.documentElement.classList.remove('dark-theme')
    return 'light'
  })

  const toggleTheme = () => {
    const nextTheme = theme === 'light' ? 'dark' : 'light'
    setTheme(nextTheme)
    try {
      localStorage.setItem('pulli-theme', nextTheme)
    } catch {
      /* ignore */
    }
    if (nextTheme === 'dark') {
      document.documentElement.classList.add('dark-theme')
    } else {
      document.documentElement.classList.remove('dark-theme')
    }
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    function handle(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setLangOpen(false)
      }
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [])

  const currentLang = LANGUAGES.find(l => l.code === lang) || LANGUAGES[0]

  return (
    <header className="navbar-clone">
      <div className="navbar-inner">
        {/* Left: Brand Logo & Title */}
        <Link to="/" className="navbar-brand">
          <div className="brand-icon-wrapper">
            <svg width="40" height="40" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* 3x3 Pulli (dots) grid */}
              <circle cx="30" cy="30" r="2.2" fill="#B88735" />
              <circle cx="50" cy="30" r="2.2" fill="#B88735" />
              <circle cx="70" cy="30" r="2.2" fill="#B88735" />
              <circle cx="30" cy="50" r="2.2" fill="#B88735" />
              <circle cx="50" cy="50" r="2.8" fill="#B88735" />
              <circle cx="70" cy="50" r="2.2" fill="#B88735" />
              <circle cx="30" cy="70" r="2.2" fill="#B88735" />
              <circle cx="50" cy="70" r="2.2" fill="#B88735" />
              <circle cx="70" cy="70" r="2.2" fill="#B88735" />
              {/* Continuous loop line (Kambi) */}
              <path d="M 50 35 C 42 22, 42 8, 50 8 C 58 8, 58 22, 50 35 C 58 35, 68 18, 75 25 C 82 32, 65 42, 65 50 C 78 46, 92 42, 92 50 C 92 58, 78 54, 65 50 C 65 58, 82 68, 75 75 C 68 82, 58 65, 50 65 C 54 78, 58 92, 50 92 C 42 92, 46 78, 50 65 C 42 65, 32 82, 25 75 C 18 68, 35 58, 35 50 C 22 54, 8 58, 8 50 C 8 42, 22 46, 35 50 C 35 42, 18 32, 25 25 C 32 18, 42 35, 50 35 Z" 
                    stroke="#B88735" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </svg>
          </div>
          <div className="brand-text">
            <span className="brand-title">PULLI</span>
            <span className="brand-subtitle">Kolam Design-Principle Engine</span>
          </div>
        </Link>

        {/* Center: Navigation Links */}
        <nav className="navbar-nav">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            {t('nav.home')}
          </NavLink>
          <NavLink to="/analyze" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            {t('nav.analyze')}
          </NavLink>
          <NavLink to="/detect" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            {t('nav.detect')}
          </NavLink>
          <NavLink to="/generate" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            {t('nav.generate')}
          </NavLink>
          <NavLink to="/explore" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            {t('nav.gallery')}
          </NavLink>
          <NavLink to="/about" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            {t('nav.about')}
          </NavLink>
          <NavLink to="/how-it-works" className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'}>
            {t('nav.howItWorks')}
          </NavLink>
        </nav>

        {/* Right: Controls */}
        <div className="navbar-controls">
          <div className="lang-dropdown" ref={dropdownRef}>
            <button
              className="btn-lang"
              onClick={() => setLangOpen(o => !o)}
              aria-haspopup="listbox"
              aria-expanded={langOpen}
            >
              <span>{currentLang.nativeName}</span>
              <ChevronDown size={14} className={langOpen ? 'chevron-open' : ''} />
            </button>
            {langOpen && (
              <ul className="lang-menu" role="listbox" aria-label="Select language">
                {LANGUAGES.map(l => (
                  <li
                    key={l.code}
                    role="option"
                    aria-selected={l.code === lang}
                    className={`lang-option${l.code === lang ? ' selected' : ''}`}
                    onClick={() => { setLanguage(l.code); setLangOpen(false) }}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { setLanguage(l.code); setLangOpen(false) } }}
                    tabIndex={0}
                  >
                    <span className="lang-script">{l.script}</span>
                    <span>{l.nativeName}</span>
                    {l.code === lang && <span className="lang-check">✓</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button className="btn-theme" onClick={toggleTheme} aria-label="Toggle Theme">
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>

          <button className="btn-login">
            <User size={16} />
            <span>Login</span>
          </button>
        </div>
      </div>
    </header>
  )
}
