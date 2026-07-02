import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/reports', label: 'Reports' },
  { to: '/subscriptions', label: 'Alerts' },
]

export default function Navbar() {
  const navigate = useNavigate()
  const location = useLocation()
  const clearTokens = useAuthStore((s) => s.clearTokens)

  function logout() {
    clearTokens()
    navigate('/login')
  }

  return (
    <nav className="bg-surface border-b border-slate-700 px-6 py-3 flex items-center justify-between">
      <Link to="/" className="text-xl font-bold text-brand-light tracking-tight">
        Zetrix
        <span className="ml-2 text-xs text-slate-400 font-normal">Global Opportunity Explorer</span>
      </Link>
      <div className="flex items-center gap-6">
        {links.map((l) => (
          <Link
            key={l.to}
            to={l.to}
            className={`text-sm transition-colors ${
              location.pathname === l.to
                ? 'text-white font-semibold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            {l.label}
          </Link>
        ))}
        <button
          onClick={logout}
          className="text-sm text-slate-400 hover:text-red-400 transition-colors ml-2"
        >
          Logout
        </button>
      </div>
    </nav>
  )
}
