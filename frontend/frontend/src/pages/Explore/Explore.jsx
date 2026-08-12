import { useState, useMemo } from 'react'
import KolamCard from '../../components/KolamCard/KolamCard'
import { kolam19 } from '../../data/kolams'
import './Explore.css'

const ITEMS_PER_PAGE = 36

export default function Explore() {
  const [search, setSearch] = useState('')
  const [visibleCount, setVisibleCount] = useState(ITEMS_PER_PAGE)

  const filteredKolams = useMemo(() => {
    if (!search.trim()) return kolam19
    const query = search.trim().toLowerCase()
    return kolam19.filter(k => 
      k.id.toString().includes(query) || 
      `kolam ${k.id}`.includes(query) ||
      `kolam19-${k.id-1}`.includes(query)
    )
  }, [search])

  const visibleKolams = useMemo(() => {
    return filteredKolams.slice(0, visibleCount)
  }, [filteredKolams, visibleCount])

  const handleLoadMore = () => {
    setVisibleCount(prev => prev + ITEMS_PER_PAGE)
  }

  return (
    <main id="main-content" className="explore-page">
      <header className="explore-header section">
        <div className="container">
          <p className="eyebrow">Kolam Explorer</p>
          <h1 className="heading-display heading-2 explore-title">
            Explore dataset: kolam19
          </h1>
          <p className="body-text explore-sub">
            400 one-stroke Pulli Kolam patterns constructed around a 37×37 dot grid.
            Select any Kolam to view its geometric properties, validity analysis, and symmetry metrics.
          </p>

          {/* Search / Filter bar */}
          <div className="explore-toolbar">
            <div className="explore-search-wrap">
              <span className="explore-search-icon" aria-hidden="true">🔍</span>
              <input
                type="text"
                className="explore-search-input"
                placeholder="Filter by Kolam number (e.g. 26, 105)..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setVisibleCount(ITEMS_PER_PAGE)
                }}
                aria-label="Filter Kolam patterns by number"
              />
              {search && (
                <button
                  className="explore-search-clear"
                  onClick={() => {
                    setSearch('')
                    setVisibleCount(ITEMS_PER_PAGE)
                  }}
                  aria-label="Clear filter"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="explore-meta label-tech">
              Showing {visibleKolams.length} of {filteredKolams.length} patterns
            </div>
          </div>
        </div>
      </header>

      {/* Grid gallery */}
      <section className="explore-gallery-section container">
        {filteredKolams.length === 0 ? (
          <div className="explore-empty">
            <p className="heading-display heading-4">No matching Kolam found.</p>
            <p className="body-text">Try searching for a number between 1 and 400.</p>
          </div>
        ) : (
          <>
            <div className="explore-grid">
              {visibleKolams.map(kolam => (
                <KolamCard key={kolam.id} kolam={kolam} />
              ))}
            </div>

            {visibleCount < filteredKolams.length && (
              <div className="explore-load-more">
                <button 
                  onClick={handleLoadMore}
                  className="btn btn--outline"
                >
                  Load More Patterns ({filteredKolams.length - visibleCount} remaining)
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  )
}
