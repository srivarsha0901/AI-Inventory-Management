import Button from './Button'
export default function StubPage({ icon, title, description, comingSoon=true }) {
  return (
    <div className="bg-white border border-[var(--border)] rounded-2xl p-16 text-center" style={{ boxShadow:'var(--shadow-sm)' }}>
      <div className="w-[72px] h-[72px] rounded-[20px] flex items-center justify-center text-3xl mx-auto mb-5 bg-[var(--teal-pale)] border-2 border-[var(--teal-border)]">{icon}</div>
      <h2 className="font-display font-bold text-[1.4rem] text-[var(--ink)] mb-2.5">{title}</h2>
      <p className="text-[0.9rem] text-[var(--muted)] leading-relaxed max-w-md mx-auto mb-7">{description}</p>
      {comingSoon && <Button variant="outline" size="md">Coming soon</Button>}
    </div>
  )
}