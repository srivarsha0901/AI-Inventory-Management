import { useAuth } from '../../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import Button from './Button'

export default function OnboardingGuard({ children }) {
  const { user }   = useAuth()
  const navigate   = useNavigate()

  if (!user?.onboarding_complete) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="max-w-[480px] w-full text-center">
          <div className="text-6xl mb-6">📦</div>
          <h2 className="font-display font-bold text-[1.8rem] text-[var(--ink)] mb-3">
            Set up your inventory first
          </h2>
          <p className="text-[0.95rem] text-[var(--muted)] mb-8 leading-relaxed">
            Before using FreshTrack, add your store's products and current stock levels.
            It only takes a few minutes!
          </p>
          <Button size="lg" className="w-full" onClick={() => navigate('/onboarding')}>
            Add my inventory →
          </Button>
        </div>
      </div>
    )
  }

  return children
}