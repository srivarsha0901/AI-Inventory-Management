import Button from './Button'
import { useNavigate } from 'react-router-dom'

export default function WaitingForData({ 
  icon = '⏳',
  title,
  message,
  actionLabel,
  actionTo,
  secondaryLabel,
  onSecondary,
}) {
  const navigate = useNavigate()

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="max-w-[480px] w-full text-center">
        <div className="text-6xl mb-6">{icon}</div>
        <h2 className="font-display font-bold text-[1.6rem] text-[var(--ink)] mb-3">
          {title}
        </h2>
        <p className="text-[0.92rem] text-[var(--muted)] mb-8 leading-relaxed">
          {message}
        </p>
        <div className="flex flex-col gap-3">
          {actionLabel && (
            <Button size="lg" className="w-full" onClick={() => navigate(actionTo)}>
              {actionLabel}
            </Button>
          )}
          {secondaryLabel && (
            <button onClick={onSecondary}
                    className="text-[0.85rem] text-[var(--muted)] hover:text-[var(--teal)]
                               bg-transparent border-0 cursor-pointer font-medium">
              {secondaryLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}