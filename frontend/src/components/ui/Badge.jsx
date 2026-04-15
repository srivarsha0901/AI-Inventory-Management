const VARIANTS = { red:'bg-red-100 text-red-600', amber:'bg-amber-100 text-amber-600', teal:'bg-[var(--teal-pale)] text-[var(--teal)]', blue:'bg-blue-50 text-blue-500', green:'bg-green-50 text-green-600', gray:'bg-gray-100 text-gray-500' }
export default function Badge({ variant='teal', children, className='' }) {
  return <span className={`inline-flex items-center text-[0.68rem] font-extrabold px-2.5 py-0.5 rounded-full tracking-wide ${VARIANTS[variant]||VARIANTS.teal} ${className}`}>{children}</span>
}