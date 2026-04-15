export default function Input({ label, type='text', id, value, onChange, placeholder, icon, error, className='', ...rest }) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {label && <label htmlFor={id} className="text-[0.72rem] font-extrabold tracking-widest uppercase text-[var(--ink2)]">{label}</label>}
      <div className="relative">
        {icon && <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-base pointer-events-none">{icon}</span>}
        <input id={id} type={type} value={value} onChange={onChange} placeholder={placeholder}
          className={`w-full bg-[var(--cream)] border-[1.5px] rounded-[10px] py-3 pr-3.5 text-[var(--ink)] text-[0.92rem] outline-none transition-all duration-200 placeholder:text-[#a8c4be] focus:bg-white focus:border-[var(--teal)] focus:shadow-[0_0_0_4px_rgba(13,148,136,0.1)] ${error ? 'border-red-400' : 'border-[var(--border)]'} ${icon ? 'pl-10' : 'pl-3.5'}`}
          {...rest} />
      </div>
      {error && <p className="text-[0.75rem] text-red-500 font-medium">{error}</p>}
    </div>
  )
}