import './ResearchPipeline.css'

const stages = [
  {
    number: '01',
    name: 'OBSERVE',
    description: 'Kolam image or coordinate trace from the dataset.',
    detail: 'CSV trace input',
  },
  {
    number: '02',
    name: 'REPRESENT',
    description: 'Coordinate normalization into a multiplicity-aware MultiGraph.',
    detail: 'NetworkX MultiGraph',
  },
  {
    number: '03',
    name: 'IDENTIFY',
    description: 'Motif extraction with D4 symmetry-aware canonicalization.',
    detail: 'D4 symmetry · motif windows',
  },
  {
    number: '04',
    name: 'VALIDATE',
    description: 'One-stroke validity checked as a graph constraint (Eulerian path).',
    detail: 'Eulerian constraint',
  },
  {
    number: '05',
    name: 'RECREATE',
    description: 'Candidate reconstruction from discovered structural rules.',
    detail: 'Research phase',
    isFuture: true,
  },
]

export default function ResearchPipeline() {
  return (
    <div className="pipeline">
      {stages.map((stage, i) => (
        <div key={stage.number} className="pipeline__item">
          {/* Stage */}
          <div className={`pipeline__stage${stage.isFuture ? ' pipeline__stage--future' : ''}`}>
            <span className="pipeline__number">{stage.number}</span>
            <div className="pipeline__content">
              <h3 className="pipeline__name">{stage.name}</h3>
              <p className="pipeline__desc">{stage.description}</p>
              <span className="pipeline__detail label-tech">{stage.detail}</span>
            </div>
            {stage.isFuture && (
              <span className="pipeline__badge">Research phase</span>
            )}
          </div>

          {/* Connector arrow (not on last item) */}
          {i < stages.length - 1 && (
            <div className="pipeline__connector" aria-hidden="true">
              <div className="pipeline__connector-line" />
              <div className="pipeline__connector-arrow">↓</div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
