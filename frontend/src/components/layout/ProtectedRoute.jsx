import { Navigate } from 'react-router-dom'
import { useAuth }  from '../../context/AuthContext'

export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--cream)]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center text-xl animate-pulse"
               style={{ background: 'linear-gradient(135deg,var(--teal),var(--teal-lt))' }}>
            🌿
          </div>
          <p className="text-[var(--muted)] text-sm font-medium">Loading FreshTrack…</p>
        </div>
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={user.role === 'cashier' ? '/pos' : '/dashboard'} replace />
  }

  return children
}