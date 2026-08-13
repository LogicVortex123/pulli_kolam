import GeneratedVariations from '../../components/GeneratedVariations/GeneratedVariations'
import './Generate.css'

export default function Generate() {
  return (
    <main id="main-content" className="generate-page">
      <header className="generate-header section section--bordered">
        <div className="container">
          <p className="eyebrow eyebrow--accent">Rule-Guided Reconstruction</p>
          <h1 className="heading-display heading-2 generate-title">
            Generate Kolam Variations
          </h1>
          <p className="body-text generate-sub">
            Novel candidates assembled from induced motif subgraphs, filtered against the Eulerian trail continuity constraint before presentation.
          </p>
        </div>
      </header>

      <section className="container section generate-content">
        <GeneratedVariations />
      </section>
    </main>
  )
}
