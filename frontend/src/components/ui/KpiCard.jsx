export default function KpiCard({ label, value, meta, icon, stripeColor, valueColor }) {
  return (
    <div className="bg-white border border-[var(--border)] rounded-[14px] p-5 relative overflow-hidden hover:-translate-y-0.5 hover:shadow-md transition-all duration-200" style={{ boxShadow:'var(--shadow-sm)' }}>
      <div className="absolute top-0 left-0 right-0 h-[3px] rounded-t-[14px]" style={{ background: stripeColor||'var(--teal)' }} />
      <div className="absolute right-4 top-1/2 -translate-y-1/2 text-4xl opacity-10 select-none">{icon}</div>
      <div className="text-[0.7rem] font-extrabold tracking-widest uppercase text-[var(--muted)] mb-2">{label}</div>
      <div className="font-display font-bold text-[2rem] leading-none mb-1.5" style={{ color: valueColor||'var(--teal)' }}>{value??'—'}</div>
      {meta && <div className="text-[0.76rem] text-[var(--muted)] font-medium">{meta}</div>}
    </div>
  )
}