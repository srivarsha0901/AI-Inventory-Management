export function Card({ children, className='' }) {
  return <div className={`bg-white border border-[var(--border)] rounded-[14px] overflow-hidden ${className}`} style={{ boxShadow:'var(--shadow-sm)' }}>{children}</div>
}
export function CardHeader({ title, icon, right, className='' }) {
  return (
    <div className={`flex items-center justify-between px-5 py-4 border-b border-[var(--border)] ${className}`}>
      <div className="flex items-center gap-2 font-bold text-[0.9rem] text-[var(--ink)]">{icon && <span>{icon}</span>}{title}</div>
      {right && <div className="flex items-center gap-2">{right}</div>}
    </div>
  )
}
export function CardBody({ children, className='' }) {
  return <div className={`p-5 ${className}`}>{children}</div>
}