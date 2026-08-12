import './About.css'

export default function About() {
  return (
    <main id="main-content" className="about-page">
      <header className="about-header section">
        <div className="container">
          <p className="eyebrow eyebrow--accent">Project Identity &amp; Attribution</p>
          <h1 className="heading-display heading-2 about-title">
            About PULLI
          </h1>
          <p className="body-text about-sub">
            Kolam Design Principle Identification &amp; Recreation — an academic research initiative studying traditional South Indian cultural artwork through computational geometry and graph theory.
          </p>
        </div>
      </header>

      <section className="container section about-content">
        <div className="about-grid">
          {/* Main overview */}
          <div className="about-main">
            <h2 className="heading-display heading-3">Research Objective</h2>
            <p className="body-text">
              Pulli Kolam is a traditional art form drawing continuous loops around dot matrices. Despite its visual complexity and intuitive creation, Kolams follow strict underlying mathematical rules governing symmetry, motif repetition, and one-stroke continuity.
            </p>
            <p className="body-text">
              The PULLI system aims to formalize these principles into a computational engine capable of analyzing existing patterns, verifying Eulerian validity constraints, and eventually generating novel valid Kolam instances.
            </p>

            <h2 className="heading-display heading-3" style={{ marginTop: '2rem' }}>Dataset Attribution</h2>
            <p className="body-text">
              This research utilizes the <strong>One-Stroke Dotted Pulli Kolam</strong> dataset hosted on Kaggle by contributor Shubha. The dataset contains image patterns and dense polyline coordinate traces for 400 Kolam designs across three dataset tiers: <code>kolam19</code>, <code>kolam29</code>, and <code>kolam109</code>.
            </p>
            <p className="body-text">
              PULLI does not claim ownership of the underlying dataset; all patterns remain attributed to their original creators and dataset maintainers.
            </p>

            <h2 className="heading-display heading-3" style={{ marginTop: '2rem' }}>Institutional Alignment</h2>
            <p className="body-text">
              Designed in accordance with academic research standards suitable for presentation at AICTE, Smart India Hackathon (SIH), and university computational research exhibitions.
            </p>
          </div>

          {/* Sidebar specs */}
          <div className="about-sidebar">
            <div className="about-card">
              <h3 className="eyebrow">Technology Stack</h3>
              <ul className="about-tech-list label-tech">
                <li><span>Language:</span> Python 3.10+</li>
                <li><span>Graph Core:</span> NetworkX (MultiGraph)</li>
                <li><span>Data Processing:</span> Pandas, NumPy</li>
                <li><span>Visualization:</span> Matplotlib</li>
                <li><span>Frontend UI:</span> React 19, Vite, Plain CSS</li>
                <li><span>API (Future):</span> FastAPI</li>
              </ul>
            </div>

            <div className="about-card">
              <h3 className="eyebrow">Project Team</h3>
              <div className="team-list body-text body-text--sm">
                <div className="team-member">
                  <strong>PULLI Research Group</strong>
                  <span>Computational Geometry &amp; Cultural Pattern Analysis</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
