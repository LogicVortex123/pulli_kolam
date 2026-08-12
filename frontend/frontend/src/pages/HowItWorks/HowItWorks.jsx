import { Link } from 'react-router-dom'
import './HowItWorks.css'

const steps = [
  {
    num: '01',
    title: 'DATASET COLLECTION',
    subtitle: 'Selection & Ingestion',
    desc: 'Kolam patterns are collected from authentic, curated datasets (kolam19, kolam29, kolam109). Each design is drawn around a structured dot matrix field.',
  },
  {
    num: '02',
    title: 'DIGITAL TRACE',
    subtitle: 'Polyline Coordinates',
    desc: 'Each pattern is represented as an ordered sequence of 2D geometric coordinates sampled at ~0.5-unit spatial resolution, storing exact stroke order.',
  },
  {
    num: '03',
    title: 'GRAPH MODELLING',
    subtitle: 'NetworkX MultiGraph',
    desc: 'The drawing structure is converted into a graph representation preserving edge multiplicity for repeated stroke strands at lattice intersection nodes.',
  },
  {
    num: '04',
    title: 'PATTERN ANALYSIS',
    subtitle: 'Symmetry & Motif Extraction',
    desc: 'The system studies reflection/rotation under Dihedral D4 symmetry groups and extracts recurring local subgraphs via fixed and adaptive radius set-cover induction.',
  },
  {
    num: '05',
    title: 'STRUCTURAL VALIDATION',
    subtitle: 'Eulerian Trail Verification',
    desc: 'Candidate patterns are evaluated against one-stroke closed loop constraints (Eulerian path verification) with 28 automated test suite assertions.',
  },
  {
    num: '06',
    title: 'RECONSTRUCTION',
    subtitle: 'Generative Synthesis (Research Phase)',
    desc: 'Discovered motif rules and symmetry constraints provide the foundation for future computational generation of valid new Kolam patterns.',
    isFuture: true,
  },
]

export default function HowItWorks() {
  return (
    <main id="main-content" className="how-it-works-page">
      <header className="how-header section section--bordered">
        <div className="container">
          <p className="eyebrow eyebrow--accent">Technical Pipeline Walkthrough</p>
          <h1 className="heading-display heading-2 how-title">
            HOW IT WORKS
          </h1>
          <p className="body-text how-sub">
            The 6-stage visual pipeline transforming traditional one-stroke Kolam drawings into verified graph structures and mathematical representations.
          </p>
        </div>
      </header>

      {/* Visual Pipeline Grid */}
      <section className="container section section--bordered">
        <div className="pipeline-grid">
          {steps.map((step) => (
            <div key={step.num} className={`pipeline-card archival-frame ${step.isFuture ? 'pipeline-card--future' : ''}`}>
              <div className="card-top">
                <span className="step-tag label-tech">{step.num} — {step.subtitle}</span>
                {step.isFuture && <span className="future-tag label-tech">IN PROGRESS</span>}
              </div>
              <h2 className="heading-display heading-4 step-heading">{step.title}</h2>
              <p className="body-text body-text--sm step-text">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Deep-Dive Technical Detail */}
      <section className="container section">
        <div className="tech-explain-grid">
          <div>
            <p className="eyebrow">GRAPH REPRESENTATION</p>
            <h2 className="heading-display heading-3" style={{ marginTop: '0.5rem' }}>
              Why MultiGraph Over Simple Graph?
            </h2>
          </div>
          <div className="body-text">
            <p>
              In traditional Kolam drawing, strokes frequently loop back alongside previously drawn strands between adjacent dots. A standard simple graph cannot capture multiple parallel edges between the same pair of nodes.
            </p>
            <p style={{ marginTop: '1rem' }}>
              PULLI utilizes NetworkX <code>MultiGraph</code> to store edge multiplicity explicitly. This allows Eulerian trail checks to evaluate the exact stroke traversal order.
            </p>
            <div style={{ marginTop: '1.5rem' }}>
              <Link to="/technology" className="btn btn--primary">
                View Full Technology Specifications →
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
