const VARIANTS = {
  primary: 'text-white font-bold border-none cursor-pointer',
  outline: 'bg-transparent border border-[var(--border)] text-[var(--muted)] hover:border-[var(--teal)] hover:text-[var(--teal)] hover:bg-[var(--teal-pale)]',
  danger:  'bg-transparent border border-[var(--border)] text-[var(--muted)] hover:border-red-300 hover:text-red-500 hover:bg-red-50',
  ghost:   'bg-transparent border-none text-[var(--muted)] hover:text-[var(--teal)] hover:bg-[var(--teal-pale)]',
}
const SIZES = {
  sm: 'text-[0.78rem] px-3 py-1.5 rounded-[7px]',
  md: 'text-[0.88rem] px-4 py-2.5 rounded-[9px]',
  lg: 'text-[0.95rem] px-6 py-3 rounded-[11px]',
}

export default function Button({ children, variant='primary', size='md', onClick, disabled=false, loading=false, className='', type='button' }) {
  const isPrimary = variant === 'primary'
  return (
    <button type={type} onClick={onClick} disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 font-semibold transition-all duration-200
        ${VARIANTS[variant]} ${SIZES[size]}
        ${disabled || loading ? 'opacity-50 cursor-not-allowed' : ''}
        ${isPrimary ? 'hover:-translate-y-px active:scale-[0.98]' : ''} ${className}`}
      style={isPrimary ? { background:'linear-gradient(135deg,var(--teal),var(--teal-lt))', boxShadow:'0 4px 16px rgba(13,148,136,0.3)' } : {}}>
      {loading && <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />}
      {children}
    </button>
  )
}