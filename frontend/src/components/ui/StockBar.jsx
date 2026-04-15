export default function StockBar({ pct=0, width=80 }) {
  const color = pct<=20 ? '#ef4444' : pct<=40 ? '#f59e0b' : 'var(--teal)'
  return (
    <div className="bg-[var(--cream)] border border-[var(--border)] rounded-full h-1.5 overflow-hidden" style={{ width }}>
      <div className="h-full rounded-full transition-all duration-500" style={{ width:`${Math.min(pct,100)}%`, background:color }} />
    </div>
  )
}