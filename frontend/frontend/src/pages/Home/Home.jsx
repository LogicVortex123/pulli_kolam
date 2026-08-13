import { Link } from 'react-router-dom'
import Hero from '../../components/Hero/Hero'
import FeatureStrip from '../../components/FeatureStrip/FeatureStrip'
import AnalysisPipeline from '../../components/AnalysisPipeline/AnalysisPipeline'
import GeneratedVariations from '../../components/GeneratedVariations/GeneratedVariations'
import { useLanguage } from '../../context/LanguageContext'
import './Home.css'

export default function Home() {
  const { t } = useLanguage()

  return (
    <main className="home-clone-main">
      {/* 1. HERO SECTION */}
      <Hero />

      {/* 2. FEATURE STRIP */}
      <FeatureStrip />

      {/* 3. MAIN CONTENT: TWO COLUMN LAYOUT */}
      <section className="main-content-section">
        <div className="main-content-container">
          {/* Static illustration, not live output -- real detection/analysis
              runs on the /detect page, backed by the actual API. */}
          <div className="illustrative-banner">
            <span className="illustrative-badge label-tech">{t('home.illustrativeBadge')}</span>
            <Link to="/detect" className="illustrative-cta">{t('home.tryDetectCta')}</Link>
          </div>
          <div className="main-content-grid">
            {/* LEFT CARD: LIVE ANALYSIS PIPELINE */}
            <AnalysisPipeline />

            {/* RIGHT CARD: GENERATED VARIATIONS & RULE SUMMARY */}
            <GeneratedVariations />
          </div>
        </div>
      </section>
    </main>
  )
}
