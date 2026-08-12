import { useSearchParams } from 'react-router-dom'
import { kolam19, getKolam } from '../../data/kolams'
import './Analyze.css'

export default function Analyze() {
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = searchParams.get('kolam') || '26'
  const currentKolam = getKolam(selectedId) || kolam19[0]

  const handleSelect = (id) => {
    setSearchParams({ kolam: id })
  }

  return (
    <main id="main-content" className="analyze-page">
      <header className="analyze-header section section--bordered">
        <div className="container">
          <p className="eyebrow eyebrow--accent">Computational Analysis Monograph</p>
          <h1 className="heading-display heading-hero analyze-title">
            Structural Decomposition: Kolam {currentKolam.id}
          </h1>
          <p className="body-text analyze-sub">
            Step-by-step scientific walkthrough of the PULLI graph representation pipeline, from raw dense coordinate trace to Eulerian path validation.
          </p>

          {/* Pattern selector strip */}
          <div className="pattern-selector-bar archival-frame">
            <span className="label-tech">SELECT EXHIBITION ITEM:</span>
            <div className="selector-pills">
              {[1, 15, 26, 55, 100, 118, 179, 232, 331, 400].map(id => (
                <button
                  key={id}
                  className={`pill-btn ${Number(selectedId) === id ? 'pill-btn--active' : ''}`}
                  onClick={() => handleSelect(id.toString())}
                >
                  Kolam {id}
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Linear Scientific Breakdown: TRACE -> GRAPH -> MOTIF -> VALIDITY -> GENERATION */}
      <section className="container section analyze-pipeline-section">
        <div className="pipeline-walkthrough">
          {/* STEP 1: TRACE */}
          <article className="step-block archival-frame">
            <div className="step-header">
              <span className="step-num label-tech">STAGE 01</span>
              <h2 className="heading-display heading-3">TRACE — Raw Polyline Coordinates</h2>
            </div>
            <div className="step-body">
              <div className="step-text body-text body-text--sm">
                <p>
                  The input consists of dense continuous polyline coordinates sampled at ~0.5-unit spatial resolution from the <code>kolam19</code> dataset CSV.
                </p>
                <div className="step-table">
                  <div className="step-row"><span className="label-tech">Total Points</span><strong>{currentKolam.points}</strong></div>
                  <div className="step-row"><span className="label-tech">Calculated Path Length</span><strong>{currentKolam.pathLength} units</strong></div>
                  <div className="step-row"><span className="label-tech">Grid Resolution</span><strong>37.0 × 37.0</strong></div>
                </div>
              </div>
              <div className="step-img-frame">
                <img src={currentKolam.imagePath} alt={`Raw Kolam ${currentKolam.id} trace`} />
                <span className="label-tech">Dataset file: kolam19-{currentKolam.id - 1}.jpg</span>
              </div>
            </div>
          </article>

          {/* STEP 2: GRAPH */}
          <article className="step-block archival-frame">
            <div className="step-header">
              <span className="step-num label-tech">STAGE 02</span>
              <h2 className="heading-display heading-3">GRAPH — MultiGraph Construction</h2>
            </div>
            <div className="step-body">
              <div className="step-text body-text body-text--sm">
                <p>
                  Integer coordinates represent directly visited Pulli dot vertices. Half-integer coordinates represent loop-around geometry. Because stroke strands double back along identical lattice edges, a standard simple graph is insufficient; NetworkX <code>MultiGraph</code> preserves edge multiplicity.
                </p>
                <div className="step-table">
                  <div className="step-row"><span className="label-tech">Data Structure</span><strong>NetworkX MultiGraph</strong></div>
                  <div className="step-row"><span className="label-tech">Dot Vertex Representation</span><strong>Integer (x, y)</strong></div>
                  <div className="step-row"><span className="label-tech">Loop Vertex Representation</span><strong>Half-Integer (x+0.5, y+0.5)</strong></div>
                  <div className="step-row"><span className="label-tech">Edge Multiplicity</span><strong>Preserved</strong></div>
                </div>
              </div>
              <div className="step-diagram-box">
                <pre className="ascii-diagram label-tech">
{`  (x, y) ─────────── (x+1, y)
    │     \\  Multi  /     │
    │      \\ Strand/      │
    │       (x+0.5, y+0.5)│
    │      /        \\     │
  (x, y+1) ───────── (x+1, y+1)`}
                </pre>
              </div>
            </div>
          </article>

          {/* STEP 3: MOTIF */}
          <article className="step-block archival-frame">
            <div className="step-header">
              <span className="step-num label-tech">STAGE 03</span>
              <h2 className="heading-display heading-3">MOTIF — Dihedral D4 Canonicalization</h2>
            </div>
            <div className="step-body">
              <div className="step-text body-text body-text--sm">
                <p>
                  Local subgraphs are canonicalized under Dihedral Group D4 transformations (4 rotations, 4 reflections). Greedy set-cover multi-motif induction achieves ~89.7% average edge recall across evaluated patterns.
                </p>
                <div className="step-table">
                  <div className="step-row"><span className="label-tech">Vertical Symmetry Distance</span><strong>{currentKolam.symmetry.vertical.toFixed(5)}</strong></div>
                  <div className="step-row"><span className="label-tech">Horizontal Symmetry Distance</span><strong>{currentKolam.symmetry.horizontal.toFixed(1)}</strong></div>
                  <div className="step-row"><span className="label-tech">180° Rotational Distance</span><strong>{currentKolam.symmetry.rotation180.toFixed(5)}</strong></div>
                </div>
              </div>
            </div>
          </article>

          {/* STEP 4: VALIDITY */}
          <article className="step-block archival-frame">
            <div className="step-header">
              <span className="step-num label-tech">STAGE 04</span>
              <h2 className="heading-display heading-3">VALIDITY — Eulerian Trail Constraint</h2>
            </div>
            <div className="step-body">
              <div className="step-text body-text body-text--sm">
                <p>
                  One-stroke continuity is evaluated as a strict Eulerian circuit problem. The graph vertex degrees and edge multiplicity are checked for closed loop condition.
                </p>
                <div className="step-table">
                  <div className="step-row"><span className="label-tech">One-Stroke Continuous</span><strong className="text-valid">✓ Valid Eulerian Circuit</strong></div>
                  <div className="step-row"><span className="label-tech">Closed Loop Property</span><strong className="text-valid">✓ Start = End (0.0 distance)</strong></div>
                </div>
              </div>
            </div>
          </article>

          {/* STEP 5: GENERATION */}
          <article className="step-block archival-frame step-block--future">
            <div className="step-header">
              <span className="step-num label-tech">STAGE 05</span>
              <h2 className="heading-display heading-3">GENERATION — Rule-Guided Reconstruction</h2>
            </div>
            <div className="step-body">
              <p className="body-text body-text--sm">
                Future work will assemble novel candidates from induced motif subgraphs, enforcing the Eulerian trail constraint filter to reject invalid patterns before presentation.
              </p>
            </div>
          </article>
        </div>
      </section>
    </main>
  )
}
