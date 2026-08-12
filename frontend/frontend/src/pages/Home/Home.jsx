import { Link } from 'react-router-dom'
import KolamCard from '../../components/KolamCard/KolamCard'
import { kolam19, featuredKolamIds, projectStats, projectStatusList } from '../../data/kolams'
import './Home.css'

const featuredKolams = featuredKolamIds.map(id => kolam19.find(k => k.id === id)).filter(Boolean)

export default function Home() {
  return (
    <main id="main-content" className="home-showcase">
      {/* ── 1. HERO SECTION ────────────────────────────────────────────── */}
      <section className="section section--bordered hero-section" aria-labelledby="hero-title">
        <div className="container">
          <div className="hero-grid">
            <div className="hero-content">
              <span className="eyebrow eyebrow--accent">PUBLIC PROJECT SHOWCASE</span>
              
              <h1 id="hero-title" className="heading-display heading-hero hero-title">
                PULLI<br />
                <span className="hero-title-sub">Computational Understanding of One-Stroke Dotted Kolam Patterns</span>
              </h1>

              <p className="body-text hero-lead">
                PULLI is a computational platform for studying, representing and analysing traditional one-stroke dotted Kolam patterns using geometric traces, graph structures and pattern-based methods.
              </p>

              <div className="hero-cta-group">
                <Link to="/explore" className="btn btn--primary">
                  Explore the Kolam Archive →
                </Link>
                <Link to="/how-it-works" className="btn btn--outline">
                  How the Project Works →
                </Link>
              </div>

              <div className="hero-dataset-tag label-tech">
                <span>COLLECTION: KOLAM19</span>
                <span className="dot-sep">•</span>
                <span>400 GEOMETRIC TRACES</span>
                <span className="dot-sep">•</span>
                <span>37×37 DOT LATTICE</span>
              </div>
            </div>

            {/* Dominant Real Kolam Visual */}
            <div className="hero-visual-frame archival-frame">
              <div className="frame-meta label-tech">
                <span>SPECIMEN ITEM #026</span>
                <span>KOLAM19-25.JPG</span>
              </div>
              <div className="frame-img-container">
                <img
                  src={kolam19.find(k => k.id === 26)?.imagePath}
                  alt="Original Kolam pattern 26 from the kolam19 dataset"
                  className="hero-img"
                />
              </div>
              <div className="frame-caption label-tech">
                <span>725 TRACE POINTS · 816.8u PATH LENGTH · CLOSED EULERIAN TRAIL</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 2. ABOUT THE PROJECT (3 PILLARS) ────────────────────────── */}
      <section className="section section--bordered about-section" aria-labelledby="about-heading">
        <div className="container">
          <div className="section-title-block">
            <p className="eyebrow">Project Overview</p>
            <h2 id="about-heading" className="heading-display heading-2">ABOUT THE PROJECT</h2>
            <p className="body-text">
              Traditional Kolams combine geometry, symmetry, repetition and continuous drawing paths. PULLI explores how these characteristics can be represented digitally and analysed computationally.
            </p>
          </div>

          <div className="pillars-grid">
            <div className="pillar-card archival-frame">
              <span className="eyebrow eyebrow--accent">PILLAR 01</span>
              <h3 className="heading-display heading-3">DIGITAL PRESERVATION</h3>
              <p className="body-text body-text--sm">
                Digitally represent traditional Kolam patterns and their geometric traces from authentic datasets into standardized vector polylines.
              </p>
            </div>

            <div className="pillar-card archival-frame">
              <span className="eyebrow eyebrow--accent">PILLAR 02</span>
              <h3 className="heading-display heading-3">COMPUTATIONAL ANALYSIS</h3>
              <p className="body-text body-text--sm">
                Study drawing paths, NetworkX MultiGraph structures, D4 dihedral group symmetry, and recurring local motif vocabularies.
              </p>
            </div>

            <div className="pillar-card archival-frame">
              <span className="eyebrow eyebrow--accent">PILLAR 03</span>
              <h3 className="heading-display heading-3">GENERATIVE POTENTIAL</h3>
              <p className="body-text body-text--sm">
                Build a foundation for computational reconstruction and future generation of valid patterns guided by Eulerian structural constraints.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. PROJECT WORKFLOW (HOW IT WORKS) ──────────────────────── */}
      <section className="section section--bordered workflow-section" aria-labelledby="workflow-heading">
        <div className="container">
          <div className="section-title-block">
            <p className="eyebrow">Technical Pipeline</p>
            <h2 id="workflow-heading" className="heading-display heading-2">HOW IT WORKS</h2>
            <p className="body-text body-text--sm">
              A 6-stage visual pipeline transforming traditional drawing traces into verified graph representations.
            </p>
          </div>

          <div className="workflow-pipeline">
            <div className="pipeline-step archival-frame">
              <span className="step-num label-tech">01 — DATASET</span>
              <h3 className="step-title">DATASET</h3>
              <p className="step-desc">Kolam patterns are collected from the selected dataset (kolam19, kolam29, kolam109).</p>
            </div>

            <div className="pipeline-step archival-frame">
              <span className="step-num label-tech">02 — DIGITAL TRACE</span>
              <h3 className="step-title">DIGITAL TRACE</h3>
              <p className="step-desc">Each pattern is represented as an ordered sequence of geometric coordinates sampled at ~0.5u resolution.</p>
            </div>

            <div className="pipeline-step archival-frame">
              <span className="step-num label-tech">03 — GRAPH</span>
              <h3 className="step-title">GRAPH</h3>
              <p className="step-desc">The drawing structure is represented computationally using NetworkX MultiGraph, preserving repeated strands.</p>
            </div>

            <div className="pipeline-step archival-frame">
              <span className="step-num label-tech">04 — ANALYSIS</span>
              <h3 className="step-title">ANALYSIS</h3>
              <p className="step-desc">The system studies dihedral D4 symmetry planes and recurring local motif structures via set-cover induction.</p>
            </div>

            <div className="pipeline-step archival-frame">
              <span className="step-num label-tech">05 — VALIDATION</span>
              <h3 className="step-title">VALIDATION</h3>
              <p className="step-desc">Candidate structures are checked against Eulerian trail constraints required for one-stroke patterns.</p>
            </div>

            <div className="pipeline-step archival-frame pipeline-step--future">
              <span className="step-num label-tech">06 — RECONSTRUCTION</span>
              <h3 className="step-title">RECONSTRUCTION</h3>
              <p className="step-desc">Discovered structures provide the foundation for future computational generation of valid patterns.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. KOLAM ARCHIVE PREVIEW ─────────────────────────────────── */}
      <section className="section section--bordered archive-preview-section" aria-labelledby="archive-heading">
        <div className="container">
          <div className="archive-preview-header">
            <div>
              <p className="eyebrow">Digital Repository</p>
              <h2 id="archive-heading" className="heading-display heading-2">EXPLORE THE KOLAM ARCHIVE</h2>
              <p className="body-text body-text--sm">
                Catalogue items from the 400-pattern kolam19 dataset. Select any specimen to inspect geometric metrics.
              </p>
            </div>
            <Link to="/explore" className="btn btn--outline">
              Browse Full Archive (400 Items) →
            </Link>
          </div>

          <div className="archive-grid-preview">
            {featuredKolams.map(k => (
              <KolamCard key={k.id} kolam={k} />
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. PROJECT STATUS CHECKLIST ─────────────────────────────── */}
      <section className="section section--bordered status-section" aria-labelledby="status-heading">
        <div className="container">
          <div className="section-title-block">
            <p className="eyebrow eyebrow--accent">Project Progress</p>
            <h2 id="status-heading" className="heading-display heading-2">PROJECT STATUS</h2>
            <p className="body-text body-text--sm">
              Transparent project roadmap and implementation milestones for institutional reviewers.
            </p>
          </div>

          <div className="status-grid archival-frame">
            {projectStatusList.map((item, index) => (
              <div key={index} className={`status-row ${item.status === 'completed' ? 'status-row--done' : 'status-row--pending'}`}>
                <span className="status-mark">{item.status === 'completed' ? '✓' : '→'}</span>
                <div className="status-info">
                  <span className="status-label">{item.label}</span>
                  <span className="status-detail label-tech">{item.detail}</span>
                </div>
                <span className="status-badge label-tech">
                  {item.status === 'completed' ? 'COMPLETED' : 'IN PROGRESS'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 6. PROJECT FINDINGS / TECHNICAL HIGHLIGHTS ─────────────── */}
      <section className="section section--bordered findings-section" aria-labelledby="findings-heading">
        <div className="container">
          <div className="section-title-block">
            <p className="eyebrow">Technical Highlights</p>
            <h2 id="findings-heading" className="heading-display heading-2">PROJECT FINDINGS &amp; ANALYSIS RESULTS</h2>
            <p className="body-text body-text--sm">
              Verified experimental measurements on the 15-pattern evaluation sample. All values represent <strong>structural edge coverage/recall</strong> (not "accuracy").
            </p>
          </div>

          <div className="findings-container archival-frame">
            <table className="findings-table">
              <thead>
                <tr>
                  <th className="label-tech">ANALYSIS METHOD</th>
                  <th className="label-tech">STRUCTURAL EDGE RECALL</th>
                  <th className="label-tech">DESCRIPTION RATIO</th>
                  <th className="label-tech">TECHNICAL EXPLANATION</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="method-name">Fixed Radius Motif Induction</td>
                  <td className="method-val">{projectStats.fixedRadius.edgeRecall}</td>
                  <td className="method-val">{projectStats.fixedRadius.descriptionRatio}</td>
                  <td className="method-desc">Standard fixed spatial window motif extraction.</td>
                </tr>
                <tr>
                  <td className="method-name">Adaptive Radius Motif Induction</td>
                  <td className="method-val metric-val--valid">{projectStats.adaptiveRadius.edgeRecall}</td>
                  <td className="method-val">{projectStats.adaptiveRadius.descriptionRatio}</td>
                  <td className="method-desc">Adaptive radius improves edge coverage to 99.5% but increases motif complexity.</td>
                </tr>
              </tbody>
            </table>

            <div className="findings-meta label-tech">
              <span>AUTOMATED TEST SUITE: {projectStats.automatedTestsPassing} TESTS PASSING</span>
              <span className="dot-sep">•</span>
              <span>EVALUATION SAMPLE: 15 PATTERNS FROM KOLAM19</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── 7. POTENTIAL IMPACT ─────────────────────────────────────── */}
      <section className="section impact-section" aria-labelledby="impact-heading">
        <div className="container">
          <div className="section-title-block">
            <p className="eyebrow eyebrow--accent">Public &amp; Institutional Value</p>
            <h2 id="impact-heading" className="heading-display heading-2">POTENTIAL IMPACT</h2>
            <p className="body-text body-text--sm">
              How the PULLI framework can support digital heritage, education, and pattern research.
            </p>
          </div>

          <div className="impact-grid">
            <div className="impact-card archival-frame">
              <h3 className="eyebrow">CULTURAL HERITAGE</h3>
              <h4 className="heading-display heading-4">Digital Preservation</h4>
              <p className="body-text body-text--sm">
                Provides a digital documentation format for preserving traditional South Indian Kolam patterns as computable vector traces.
              </p>
            </div>

            <div className="impact-card archival-frame">
              <h3 className="eyebrow">EDUCATION</h3>
              <h4 className="heading-display heading-4">STEM &amp; Ethnomathematics</h4>
              <p className="body-text body-text--sm">
                Enables interactive exploration of geometry, symmetry, graph structures, and traditional indigenous mathematical practices.
              </p>
            </div>

            <div className="impact-card archival-frame">
              <h3 className="eyebrow">RESEARCH &amp; INNOVATION</h3>
              <h4 className="heading-display heading-4">Pattern Systems</h4>
              <p className="body-text body-text--sm">
                Establishes a computational framework for studying continuous structured visual patterns and loop-around graph topologies.
              </p>
            </div>

            <div className="impact-card archival-frame">
              <h3 className="eyebrow">DIGITAL HERITAGE</h3>
              <h4 className="heading-display heading-4">Searchable Repositories</h4>
              <p className="body-text body-text--sm">
                Lays the foundation for searchable digital archives and computational exploration of traditional artistic designs.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
