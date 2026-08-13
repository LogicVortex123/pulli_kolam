import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../App'
import Footer from '../components/Footer/Footer'
import { LanguageProvider } from '../context/LanguageContext'

// Every path App.jsx registers a <Route> for. Kept in sync manually --
// if this list drifts from App.jsx, the "renders without crashing" cases
// below stop being representative.
const STATIC_ROUTES = [
  '/', '/project', '/how-it-works', '/explore', '/analyze', '/generate',
  '/detect', '/technology', '/impact', '/about', '/this-route-does-not-exist',
]

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <LanguageProvider>
        <App />
      </LanguageProvider>
    </MemoryRouter>
  )
}

describe('App routing', () => {
  it.each(STATIC_ROUTES)('renders %s without crashing', (path) => {
    renderAt(path)
    expect(screen.getAllByRole('banner').length).toBeGreaterThan(0)
  })

  it('renders a kolam detail page for a known id', () => {
    renderAt('/explore/26')
    expect(screen.getAllByRole('banner').length).toBeGreaterThan(0)
  })
})

describe('Footer links', () => {
  it('only links to routes App.jsx actually registers', () => {
    render(
      <MemoryRouter>
        <LanguageProvider>
          <Footer />
        </LanguageProvider>
      </MemoryRouter>
    )
    const links = screen.queryAllByRole('link').map((a) => a.getAttribute('href'))
    for (const href of links) {
      expect(STATIC_ROUTES).toContain(href)
    }
  })
})
