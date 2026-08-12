import { Link } from 'react-router-dom'
import './Footer.css'

export default function Footer() {
  return (
    <footer className="site-footer" role="contentinfo">
      <div className="container">
        <div className="footer__top">
          {/* Brand Identity */}
          <div className="footer__brand">
            <div className="footer__wordmark">
              <svg viewBox="0 0 42 28" fill="none" aria-hidden="true" className="footer__mark">
                <circle cx="7" cy="7" r="2.2" fill="currentColor"/>
                <circle cx="21" cy="7" r="2.2" fill="currentColor"/>
                <circle cx="35" cy="7" r="2.2" fill="currentColor"/>
                <circle cx="14" cy="14" r="2.2" fill="currentColor"/>
                <circle cx="28" cy="14" r="2.2" fill="currentColor"/>
                <circle cx="7" cy="21" r="2.2" fill="currentColor"/>
                <circle cx="21" cy="21" r="2.2" fill="currentColor"/>
                <circle cx="35" cy="21" r="2.2" fill="currentColor"/>
                <line x1="7" y1="7" x2="14" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.35"/>
                <line x1="21" y1="7" x2="14" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.35"/>
                <line x1="21" y1="7" x2="28" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.35"/>
                <line x1="35" y1="7" x2="28" y2="14" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.35"/>
                <line x1="14" y1="14" x2="7" y2="21" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.35"/>
                <line x1="14" y1="14" x2="21" y2="21" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.35"/>
                <line x1="28" y1="14" x2="21" y2="21" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.35"/>
                <line x1="28" y1="14" x2="35" y2="21" stroke="currentColor" strokeWidth="0.8" strokeOpacity="0.35"/>
              </svg>
              <span className="footer__name">PULLI</span>
            </div>
            <p className="footer__tagline">
              Computational Understanding of<br />
              One-Stroke Dotted Kolam Patterns
            </p>
            <p className="footer__description">
              A computational platform for studying, representing and analysing traditional
              one-stroke dotted Kolam patterns using geometric traces and graph structures.
            </p>
          </div>

          {/* Project Navigation */}
          <div className="footer__col">
            <h3 className="footer__col-heading">Navigation</h3>
            <nav aria-label="Footer navigation">
              <Link to="/" className="footer__link">Home</Link>
              <Link to="/project" className="footer__link">Project Overview</Link>
              <Link to="/how-it-works" className="footer__link">How It Works</Link>
              <Link to="/explore" className="footer__link">Explore Archive</Link>
              <Link to="/technology" className="footer__link">Technology</Link>
              <Link to="/impact" className="footer__link">Potential Impact</Link>
              <Link to="/about" className="footer__link">About &amp; Team</Link>
            </nav>
          </div>

          {/* Dataset Attribution */}
          <div className="footer__col">
            <h3 className="footer__col-heading">Dataset Attribution</h3>
            <div className="footer__stack">
              <p className="footer__link" style={{ cursor: 'default' }}>
                One-Stroke Dotted Pulli Kolam
              </p>
              <a
                href="https://www.kaggle.com/datasets/shubha1011/one-stroke-dotted-pulli-kolam"
                target="_blank"
                rel="noopener noreferrer"
                className="footer__link"
              >
                Source: Kaggle Dataset ↗
              </a>
              <p className="footer__note" style={{ textAlign: 'left', marginTop: '0.5rem' }}>
                Dataset contains kolam19, kolam29, and kolam109 collections.
              </p>
            </div>
          </div>
        </div>

        <div className="footer__bottom">
          <hr className="rule" />
          <div className="footer__bottom-inner">
            <p className="footer__copy">
              © 2026 PULLI Project. Public digital-heritage presentation.
            </p>
            <p className="footer__note">
              PULLI is an independent computational project for digital-heritage exploration.
              Not affiliated with AICTE or government bodies unless officially specified.
            </p>
          </div>
        </div>
      </div>
    </footer>
  )
}
