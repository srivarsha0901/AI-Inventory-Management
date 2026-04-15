import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const PAGE_TITLES = {
  '/dashboard':    'Dashboard',
  '/analytics':    'Analytics',
  '/inventory':    'Stock Manager',
  '/alerts':       'Alerts',
  '/ocr':          'OCR Invoices',
  '/forecast':     'Forecasting',
  '/reorder':      'Reorder Engine',
  '/pos':          'POS Billing',
  '/transactions': 'Transactions',
}

export default function Topbar() {
  const { user, logout } = useAuth()
  const location         = useLocation()
  const navigate         = useNavigate()
  const title            = PAGE_TITLES[location.pathname] || 'FreshTrack'
  const isManager        = user?.role === 'manager'

  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  })

  return (
    <header
      className="fixed top-0 right-0 h-16 bg-white border-b border-[var(--border)] flex items-center justify-between px-7 z-40"
      style={{ left: '256px', boxShadow: '0 1px 0 var(--border)' }}
    >
      {/* Left */}
      <div className="flex items-center gap-3">
        <h1 className="font-display font-bold text-[1.15rem] text-[var(--ink)] tracking-tight">
          {title}
        </h1>
        <span
          className={`text-[0.68rem] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wide
            ${isManager
              ? 'bg-[var(--teal-pale)] text-[var(--teal)] border border-[var(--teal-border)]'
              : 'bg-blue-50 text-blue-500 border border-blue-200'
            }`}
        >
          {user?.role}
        </span>
      </div>

      {/* Right */}
      <div className="flex items-center gap-2.5">
        <span className="text-[0.78rem] text-[var(--muted)] font-medium mr-1">{today}</span>

        {/* Notification bell */}
        <button
          onClick={() => navigate('/alerts')}
          className="relative w-9 h-9 rounded-[9px] bg-[var(--cream)] border border-[var(--border)] flex items-center justify-center text-base hover:bg-[var(--teal-pale)] hover:border-[var(--teal-border)] transition-all"
        >
          🔔
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
        </button>

        {/* Settings */}
        <button className="w-9 h-9 rounded-[9px] bg-[var(--cream)] border border-[var(--border)] flex items-center justify-center text-base hover:bg-[var(--teal-pale)] hover:border-[var(--teal-border)] transition-all">
          ⚙️
        </button>

        {/* Sign out */}
        <button
          onClick={logout}
          className="text-[0.78rem] font-semibold px-4 py-2 rounded-[8px] border border-[var(--border)] text-[var(--muted)] hover:border-red-300 hover:text-red-500 hover:bg-red-50 transition-all"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}