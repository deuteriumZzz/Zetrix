import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const token = useAuthStore((state) => state.accessToken)
  const clearTokens = useAuthStore((state) => state.clearTokens)
  const sectionHref = (section: string) => location.pathname === '/' ? `#${section}` : `/#${section}`

  function logout() {
    clearTokens()
    navigate('/login')
    setMenuOpen(false)
  }

  function closeMenu() {
    setMenuOpen(false)
  }

  return (
    <header className="zh-site-header">
      <Link to="/" className="zh-wordmark" aria-label="Zetrix home" onClick={closeMenu}>
        <span className="zh-mark" aria-hidden="true" />
        <span className="zh-wordmark-text">ZETRIX</span>
      </Link>
      <nav className={`zh-header-nav ${menuOpen ? 'is-open' : ''}`} aria-label="Main navigation">
        <a href={sectionHref('about')} onClick={closeMenu}>About</a>
        <a href={sectionHref('technology')} onClick={closeMenu}>Technology</a>
        <a href={sectionHref('use-cases')} onClick={closeMenu}>Use cases</a>
        <a href={sectionHref('regions')} onClick={closeMenu}>Regions</a>
      </nav>
      <div className="zh-header-actions">
        {token ? (
          <>
            <Link to="/reports">Reports</Link>
            <button className="zh-logout-link" type="button" onClick={logout}>Log out</button>
          </>
        ) : (
          <>
            <Link to="/login">Sign in</Link>
            <Link to="/register" className="zh-access-link">Early access <span aria-hidden="true">↗</span></Link>
          </>
        )}
        <button
          className="zh-menu-toggle"
          type="button"
          aria-expanded={menuOpen}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? 'Close' : 'Menu'}
        </button>
      </div>
    </header>
  )
}
