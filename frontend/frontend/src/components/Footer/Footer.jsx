import KolamCornerDecoration from '../kolam/KolamCornerDecoration'
import KolamDecoration from '../kolam/KolamDecoration'
import './Footer.css'

export default function Footer() {
  return (
    <footer className="footer-clone">
      <KolamCornerDecoration position="bottom-left" />
      <KolamCornerDecoration position="bottom-right" />

      <div className="footer-inner">
        <div className="footer-left">
          <span>&copy; 2024 PULLI &ndash; Kolam Design-Principle Engine</span>
        </div>

        <div className="footer-center">
          <span>AICTE &ndash; Heritage &amp; Culture Initiative</span>
        </div>
      </div>

      {/* Decorative Bottom Pattern Overlay */}
      <div className="footer-pattern">
        <KolamDecoration variant="horizontal" height="12px" />
      </div>
    </footer>
  )
}
