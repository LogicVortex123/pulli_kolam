import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { detect, analyze, reconstruct, compareDetectors } from '../../lib/api/kolam'
import { categorizeCompareDots } from '../../lib/api/kolam'
import { validateImageFile } from '../../lib/validateImageFile'
import './Detect.css'

const MODES = [
  { id: 'classical', label: 'Classical' },
  { id: 'ml', label: 'ML' },
  { id: 'compare', label: 'Compare' },
]

export default function Detect() {
  const location = useLocation()
  const [file, setFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [mode, setMode] = useState('classical')
  const [status, setStatus] = useState('idle') // idle | loading | success | error
  const [errorMsg, setErrorMsg] = useState(null)
  const [detectResult, setDetectResult] = useState(null)
  const [compareResult, setCompareResult] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [reconstruction, setReconstruction] = useState(null)
  const [reconstructing, setReconstructing] = useState(false)
  const [reconstructError, setReconstructError] = useState(null)
  const [analysisError, setAnalysisError] = useState(null)
  const [imgNaturalSize, setImgNaturalSize] = useState(null)
  const [imgRenderedSize, setImgRenderedSize] = useState(null)
  const imgRef = useRef(null)
  const fileInputRef = useRef(null)

  const onFileSelected = useCallback((f) => {
    if (!f) return
    const result = validateImageFile(f)
    if (!result.valid) {
      setFile(null)
      setPreviewUrl(null)
      setStatus('error')
      setErrorMsg(result.message)
      return
    }
    setFile(f)
    setPreviewUrl(URL.createObjectURL(f))
    setDetectResult(null)
    setCompareResult(null)
    setAnalysis(null)
    setAnalysisError(null)
    setReconstruction(null)
    setReconstructError(null)
    setStatus('idle')
    setErrorMsg(null)
  }, [])

  // A file handed off from the homepage's upload CTA (Hero.jsx) arrives
  // via router state -- pick it up once on mount so the user doesn't have
  // to re-select it here. Deferred a tick so this doesn't set state
  // synchronously within the effect body (react-hooks/set-state-in-effect).
  useEffect(() => {
    const incoming = location.state?.incomingFile
    if (!incoming) return
    const id = setTimeout(() => onFileSelected(incoming), 0)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (f) onFileSelected(f)
  }, [onFileSelected])

  const onImageLoad = () => {
    const img = imgRef.current
    if (!img) return
    setImgNaturalSize({ width: img.naturalWidth, height: img.naturalHeight })
    setImgRenderedSize({ width: img.clientWidth, height: img.clientHeight })
  }

  const handleAnalyze = async () => {
    if (!file) return
    setStatus('loading')
    setErrorMsg(null)
    setDetectResult(null)
    setCompareResult(null)
    setAnalysis(null)
    setAnalysisError(null)
    setReconstruction(null)
    setReconstructError(null)

    if (mode === 'compare') {
      const { data, error } = await compareDetectors(file)
      if (error) {
        setStatus('error')
        setErrorMsg(describeError(error))
        return
      }
      setCompareResult(data)
      setStatus('success')
      return
    }

    const { data, error } = await detect(file, mode)
    if (error) {
      setStatus('error')
      setErrorMsg(describeError(error))
      return
    }
    setDetectResult(data)

    const { data: analyzeData, error: analyzeErr } = await analyze(file, mode)
    if (analyzeData) {
      setAnalysis(analyzeData)
    } else if (analyzeErr) {
      // Detection succeeded (result above is real and shown); only the
      // follow-up structural-analysis call failed -- say that specifically
      // rather than silently omitting the section or claiming everything failed.
      setAnalysisError(describeError(analyzeErr))
    }

    setStatus('success')
  }

  const handleReconstruct = async () => {
    if (!file || mode === 'compare') return
    setReconstructing(true)
    setReconstructError(null)
    const { data, error } = await reconstruct(file, mode)
    setReconstructing(false)
    if (error) {
      setReconstructError(describeError(error))
      return
    }
    setReconstruction(data)
  }

  const scale = imgNaturalSize && imgRenderedSize ? imgRenderedSize.width / imgNaturalSize.width : 1

  // The backend's `agreement` counts (api/main.py) match each classical dot to
  // its single nearest ML dot independently, without deduplicating which ML
  // dot was already claimed -- on images with a large count mismatch this can
  // double-count the same ML dot as "agreeing" with several classical dots,
  // which can even push ml_only negative. categorizeCompareDots() (used for
  // the overlay markers below) does a proper one-to-one match, so the summary
  // numbers are derived from that instead of trusting compareResult.agreement
  // directly -- never show a number known to be arithmetically wrong.
  const compareCounts = compareResult ? categorizeCompareDots(compareResult) : null

  return (
    <main id="main-content" className="detect-page">
      <header className="detect-header section section--bordered">
        <div className="container">
          <p className="eyebrow eyebrow--accent">Live Detection Workflow</p>
          <h1 className="heading-display heading-hero detect-title">Detect &amp; Analyze a Kolam</h1>
          <p className="body-text detect-sub">
            Upload a photograph of a Pulli Kolam. Choose the classical deterministic detector, the experimental
            ML detector (M4.2, 128&times;128), or run both side by side.
          </p>
        </div>
      </header>

      <section className="container section detect-body-section">
        <div className="detect-grid">
          {/* UPLOAD PANEL */}
          <div className="detect-upload-panel archival-frame">
            <div
              className="dropzone"
              onDragOver={(e) => e.preventDefault()}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              {previewUrl ? (
                <div className="preview-wrapper">
                  <img
                    ref={imgRef}
                    src={previewUrl}
                    alt="Uploaded Kolam"
                    onLoad={onImageLoad}
                    className="preview-img"
                  />
                  <DotOverlay
                    mode={mode}
                    detectResult={detectResult}
                    compareResult={compareResult}
                    scale={scale}
                  />
                </div>
              ) : (
                <p className="dropzone-label label-tech">Drag &amp; drop an image, or click to browse</p>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/bmp"
              hidden
              onChange={(e) => onFileSelected(e.target.files?.[0])}
            />

            <div className="detector-selector">
              <span className="label-tech">DETECTOR:</span>
              <div className="detector-radios">
                {MODES.map((m) => (
                  <label key={m.id} className={`detector-radio ${mode === m.id ? 'detector-radio--active' : ''}`}>
                    <input
                      type="radio"
                      name="detector"
                      value={m.id}
                      checked={mode === m.id}
                      onChange={() => setMode(m.id)}
                    />
                    {m.label}
                  </label>
                ))}
              </div>
            </div>

            <button className="btn-primary analyze-btn" disabled={!file || status === 'loading'} onClick={handleAnalyze}>
              {status === 'loading' ? 'Analyzing…' : 'Analyze Kolam'}
            </button>

            {mode !== 'compare' && status === 'success' && detectResult && (
              <button
                className="btn btn--outline reconstruct-btn"
                disabled={reconstructing}
                onClick={handleReconstruct}
              >
                {reconstructing ? 'Reconstructing…' : 'Reconstruct from Motifs'}
              </button>
            )}

            {status === 'error' && (
              <p className="detect-error" role="alert">{errorMsg}</p>
            )}
            {reconstructError && (
              <p className="detect-error" role="alert">{reconstructError}</p>
            )}
          </div>

          {/* RESULT PANEL */}
          <div className="detect-result-panel">
            {status === 'idle' && (
              <p className="body-text body-text--sm detect-placeholder">
                Results will appear here after you upload an image and choose a detector.
              </p>
            )}

            {status === 'success' && !(mode === 'compare' ? compareResult : detectResult) && (
              <p className="body-text body-text--sm detect-placeholder">
                Switched detector -- click &quot;Analyze Kolam&quot; to run {mode === 'compare' ? 'a comparison' : `the ${mode} detector`} on this image.
              </p>
            )}

            {mode !== 'compare' && detectResult && (
              <div className="archival-frame result-card">
                <h2 className="heading-display heading-3">Detection Result</h2>
                <div className="step-table">
                  <div className="step-row"><span className="label-tech">Detected dots</span><strong>{detectResult.count}</strong></div>
                  <div className="step-row"><span className="label-tech">Processing</span><strong>{detectResult.processing_ms} ms</strong></div>
                  <div className="step-row"><span className="label-tech">Detector</span><strong>{detectResult.detector}</strong></div>
                  {detectResult.model_version && (
                    <div className="step-row"><span className="label-tech">Model</span><strong>{detectResult.model_version}</strong></div>
                  )}
                </div>
              </div>
            )}

            {mode === 'compare' && compareResult && (
              <div className="archival-frame result-card">
                <h2 className="heading-display heading-3">Detector Comparison</h2>
                <div className="compare-columns">
                  <div className="compare-col">
                    <span className="label-tech">CLASSICAL</span>
                    <div className="step-row"><span>Dots</span><strong>{compareResult.classical.count}</strong></div>
                    <div className="step-row"><span>Time</span><strong>{compareResult.classical.processing_ms} ms</strong></div>
                    {compareResult.classical.error && <p className="detect-error">{compareResult.classical.error}</p>}
                  </div>
                  <div className="compare-col">
                    <span className="label-tech">ML</span>
                    <div className="step-row"><span>Dots</span><strong>{compareResult.ml.count}</strong></div>
                    <div className="step-row"><span>Time</span><strong>{compareResult.ml.processing_ms} ms</strong></div>
                    {compareResult.ml.error && <p className="detect-error">{compareResult.ml.error}</p>}
                  </div>
                </div>
                <div className="step-table">
                  <div className="step-row"><span className="label-tech">Agreeing dots</span><strong className="legend-agree">{compareCounts.agree.length}</strong></div>
                  <div className="step-row"><span className="label-tech">ML only</span><strong className="legend-ml">{compareCounts.mlOnly.length}</strong></div>
                  <div className="step-row"><span className="label-tech">Classical only</span><strong className="legend-classical">{compareCounts.classicalOnly.length}</strong></div>
                </div>
                <div className="overlay-legend">
                  <span><i className="swatch legend-agree" /> Agreement</span>
                  <span><i className="swatch legend-ml" /> ML-only</span>
                  <span><i className="swatch legend-classical" /> Classical-only</span>
                </div>
              </div>
            )}

            {analysis && (
              <div className="archival-frame result-card">
                <h2 className="heading-display heading-3">Structural Analysis</h2>
                <div className="step-table">
                  <div className="step-row"><span className="label-tech">Dot count</span><strong>{analysis.dot_count}</strong></div>
                  <div className="step-row"><span className="label-tech">Graph nodes</span><strong>{analysis.graph.nodes}</strong></div>
                  <div className="step-row"><span className="label-tech">Graph edges</span><strong>{analysis.graph.edges}</strong></div>
                  <div className="step-row"><span className="label-tech">Distinct edges</span><strong>{analysis.graph.distinct_edges}</strong></div>
                  <div className="step-row"><span className="label-tech">Motif count</span><strong>{analysis.motifs.motif_count}</strong></div>
                  <div className="step-row"><span className="label-tech">Eulerian circuit</span><strong>{analysis.validity.is_eulerian_circuit ? 'Valid' : 'No'}</strong></div>
                  <div className="step-row"><span className="label-tech">Connected</span><strong>{analysis.validity.largest_component_covers_all_nodes ? 'Yes' : 'No'}</strong></div>
                </div>
              </div>
            )}

            {analysisError && (
              <p className="detect-error" role="alert">
                Detection succeeded (shown above), but structural analysis failed: {analysisError}
              </p>
            )}

            {reconstruction && (
              <div className="archival-frame result-card">
                <h2 className="heading-display heading-3">Reconstruction</h2>
                {reconstruction.reconstruction.note ? (
                  <p className="body-text body-text--sm">{reconstruction.reconstruction.note}</p>
                ) : (
                  <div className="step-table">
                    <div className="step-row">
                      <span className="label-tech">Structurally valid</span>
                      <strong className={reconstruction.reconstruction.is_valid ? 'text-valid' : ''}>
                        {reconstruction.reconstruction.is_valid ? '✓ Valid' : 'No — see below'}
                      </strong>
                    </div>
                    <div className="step-row"><span className="label-tech">Motif-covered edges</span><strong>{reconstruction.reconstruction.motif_edges}</strong></div>
                    <div className="step-row"><span className="label-tech">Residual edges</span><strong>{reconstruction.reconstruction.residual_edges}</strong></div>
                    <div className="step-row"><span className="label-tech">Connected components</span><strong>{reconstruction.reconstruction.connectivity.connected_components}</strong></div>
                    <div className="step-row"><span className="label-tech">Fully connected</span><strong>{reconstruction.reconstruction.connectivity.largest_component_covers_all_nodes ? 'Yes' : 'No'}</strong></div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  )
}

function DotOverlay({ mode, detectResult, compareResult, scale }) {
  if (mode !== 'compare' && detectResult) {
    return (
      <svg className="dot-overlay-svg">
        {detectResult.detections.map((d, i) => (
          <circle key={i} cx={d.x * scale} cy={d.y * scale} r={4} className="dot-marker dot-marker--single" />
        ))}
      </svg>
    )
  }
  if (mode === 'compare' && compareResult) {
    const { agree, mlOnly, classicalOnly } = categorizeCompareDots(compareResult)
    return (
      <svg className="dot-overlay-svg">
        {agree.map((d, i) => <circle key={`a${i}`} cx={d.x * scale} cy={d.y * scale} r={4} className="dot-marker legend-agree" />)}
        {mlOnly.map((d, i) => <circle key={`m${i}`} cx={d.x * scale} cy={d.y * scale} r={4} className="dot-marker legend-ml" />)}
        {classicalOnly.map((d, i) => <circle key={`c${i}`} cx={d.x * scale} cy={d.y * scale} r={4} className="dot-marker legend-classical" />)}
      </svg>
    )
  }
  return null
}

function describeError(error) {
  switch (error.kind) {
    case 'backend_unavailable':
      return 'Could not reach the PULLI backend. Make sure the API server is running.'
    case 'timeout':
      return 'The request timed out. Try a smaller image or try again.'
    case 'model_unavailable':
      return 'The ML detector is currently unavailable on the server.'
    case 'invalid_image':
      return error.message || 'That file could not be processed as an image.'
    default:
      return error.message || 'Something went wrong.'
  }
}
