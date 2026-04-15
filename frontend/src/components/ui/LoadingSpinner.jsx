export default function LoadingSpinner({ message='Loading…' }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div className="w-11 h-11 rounded-xl flex items-center justify-center text-xl"
           style={{ background:'linear-gradient(135deg,var(--teal),var(--teal-lt))', boxShadow:'0 4px 16px rgba(13,148,136,0.3)', animation:'pulse 1.4s ease-in-out infinite' }}>
        🌿
      </div>
      <p className="text-[var(--muted)] text-sm font-medium">{message}</p>
    </div>
  )
}