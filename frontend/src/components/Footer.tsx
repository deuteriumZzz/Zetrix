import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="zh-site-footer">
      <Link to="/" className="zh-wordmark" aria-label="Zetrix home">
        <span className="zh-mark" aria-hidden="true" />
        <span className="zh-wordmark-text">ZETRIX</span>
      </Link>
      <nav className="zh-footer-nav" aria-label="Footer navigation">
        <a href="/#about">About</a>
        <a href="/#technology">Technology</a>
        <a href="/#use-cases">Use cases</a>
        <Link to="/pricing">Pricing</Link>
        <Link to="/terms">Terms</Link>
        <Link to="/privacy">Privacy</Link>
      </nav>
      <div className="zh-footer-right"><span>© {new Date().getFullYear()} Zetrix</span><Link to="/register">Request access ↗</Link></div>
    </footer>
  )
}
