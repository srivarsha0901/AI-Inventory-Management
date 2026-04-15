import { NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useApi } from '../../hooks/useApi'
import { alertService } from '../../services/apiServices'

const MANAGER_NAV = [
  {
    section: 'Overview',
    items: [
      { to: '/dashboard', icon: '📊', label: 'Dashboard' },
      { to: '/analytics', icon: '📈', label: 'Analytics' },
    ],
  },
  {
    section: 'Inventory',
    items: [
      { to: '/inventory', icon: '📦', label: 'Stock Manager' },
      { to: '/alerts',    icon: '⚠️', label: 'Alerts' },
      { to: '/ocr',       icon: '🧾', label: 'OCR Invoices' },
    ],
  },
  {
    section: 'Intelligence',
    items: [
      { to: '/forecast', icon: '🤖', label: 'Forecasting' },
      { to: '/reorder',  icon: '🔁', label: 'Reorder Engine' },
    ],
  },
  {
    section: 'Team',
    items: [
      { to: '/staff', icon: '👥', label: 'Staff Management' },
      { to: '/pos',   icon: '💳', label: 'POS Billing' },
    ],
  },
]

const CASHIER_NAV = [
  {
    section: 'Billing',
    items: [
      { to: '/pos',          icon: '💳', label: 'POS Billing' },
      { to: '/transactions', icon: '🧾', label: 'My Transactions' },
    ],
  },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const isManager = user?.role === 'manager'
  const navGroups = isManager ? MANAGER_NAV : CASHIER_NAV

  const { data: alertData } = useApi(alertService.getAll)
  const alertCount = alertData?.data?.filter(a => a.severity === 'critical').length || 0

  return (
    <aside className="fixed top-0 left-0 w-64 h-screen bg-white border-r border-[var(--border)] flex flex-col z-50"
           style={{ boxShadow: 'var(--shadow-md)' }}>

      {/* Logo */}
      <div className="px-5 py-5 border-b border-[var(--border)] flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
             style={{ background: 'linear-gradient(135deg,var(--teal),var(--teal-lt))', boxShadow: '0 4px 12px rgba(13,148,136,0.28)' }}>
          🌿
        </div>
        <div>
          <div className="font-display font-bold text-[1.15rem] text-[var(--ink)] leading-none">
            Fresh<span className="text-[var(--teal)]">Track</span>
          </div>
          <div className="text-[0.62rem] text-[var(--muted)] font-medium mt-0.5">Inventory Intelligence</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2">
        {navGroups.map((group) => (
          <div key={group.section}>
            <div className="px-5 pt-4 pb-1.5 text-[0.62rem] font-extrabold tracking-widest uppercase text-[var(--muted)]">
              {group.section}
            </div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3.5 py-2.5 mx-2.5 rounded-[9px] text-sm font-medium
                   transition-all duration-150 ${
                    isActive
                      ? 'text-[var(--teal)] font-bold border border-[var(--teal-border)]'
                      : 'text-[var(--muted)] hover:bg-[var(--teal-pale)] hover:text-[var(--teal)]'
                  }`
                }
                style={({ isActive }) =>
                  isActive
                    ? { background: 'linear-gradient(135deg,var(--teal-pale),#d1fae5)', boxShadow: 'var(--shadow-sm)' }
                    : {}
                }
              >
                <span className="w-5 text-center text-base flex-shrink-0">{item.icon}</span>
                <span className="flex-1">{item.label}</span>
                {item.to === '/alerts' && alertCount > 0 && (
                  <span className="text-[0.65rem] font-extrabold px-1.5 py-0.5 rounded-full bg-red-100 text-red-600">
                    {alertCount}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="p-3.5 border-t border-[var(--border)] bg-[var(--cream)]">
        <div className="flex items-center gap-2.5 p-2.5 rounded-[10px] bg-white border border-[var(--border)]
                        cursor-pointer hover:shadow-md transition-shadow"
             style={{ boxShadow: 'var(--shadow-sm)' }}>
          <div className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
               style={{ background: 'linear-gradient(135deg,var(--teal),var(--teal-lt))', boxShadow: '0 2px 8px rgba(13,148,136,0.3)' }}>
            {user?.name?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[0.84rem] font-bold text-[var(--ink)] truncate">{user?.name}</div>
            <div className="text-[0.7rem] text-[var(--muted)] capitalize">{user?.role}</div>
          </div>
          <button onClick={logout} title="Sign out"
                  className="text-[var(--muted)] hover:text-red-500 transition-colors text-base">
            ↩
          </button>
        </div>
      </div>
    </aside>
  )
}