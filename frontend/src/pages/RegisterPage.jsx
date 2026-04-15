import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authService } from '../services/apiServices'
import Input  from '../components/ui/Input'
import Button from '../components/ui/Button'

export default function RegisterPage() {
  const { login }  = useAuth()
  const navigate   = useNavigate()

  const [step, setStep] = useState(1) // 1 = account, 2 = store info
  const [form, setForm] = useState({
    name: '', email: '', password: '', confirm: '', store_name: '', address: ''
  })
  const [error,   setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k) => (e) => setForm((p) => ({ ...p, [k]: e.target.value }))

  const handleNext = (e) => {
    e.preventDefault()
    setError('')
    if (!form.name || !form.email || !form.password)
      return setError('Please fill all fields.')
    if (form.password !== form.confirm)
      return setError('Passwords do not match.')
    if (form.password.length < 6)
      return setError('Password must be at least 6 characters.')
    setStep(2)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.store_name) return setError('Store name is required.')
    setLoading(true)
    try {
      const res = await authService.register({
        name:       form.name,
        email:      form.email,
        password:   form.password,
        store_name: form.store_name,
        address:    form.address,
      })
      login(res.data.user, res.data.token)
      navigate('/onboarding', { replace: true })
    } catch (err) {
      setError(err.response?.data?.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-[var(--cream)] overflow-hidden relative">

      {/* Blob decorations */}
      <div className="pointer-events-none fixed -top-44 -right-44 w-[600px] h-[600px] rounded-full"
           style={{ background: 'radial-gradient(ellipse at center,#ccfbf1 0%,#a7f3d0 40%,transparent 70%)',
                    animation: 'blobDrift 12s ease-in-out infinite alternate' }} />
      <div className="pointer-events-none fixed -bottom-52 -left-52 w-[700px] h-[700px] rounded-full"
           style={{ background: 'radial-gradient(ellipse at center,#dbeafe 0%,#bfdbfe 40%,transparent 70%)',
                    animation: 'blobDrift2 14s ease-in-out infinite alternate' }} />

      {/* LEFT PANEL */}
      <div className="flex-1 flex items-center justify-center px-14 py-16 relative z-10">
        <div className="max-w-[420px] w-full">
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 rounded-[14px] flex items-center justify-center text-[1.4rem]"
                 style={{ background: 'linear-gradient(135deg,var(--teal),var(--teal-lt))',
                          boxShadow: '0 8px 24px rgba(13,148,136,0.3)' }}>
              🌿
            </div>
            <div className="font-display font-bold text-[1.5rem] text-[var(--ink)] tracking-tight">
              Fresh<span className="text-[var(--teal)]">Track</span>
            </div>
          </div>

          <div className="inline-flex items-center gap-1.5 text-[0.7rem] font-bold tracking-widest uppercase
                          text-[var(--teal)] bg-[var(--teal-pale)] border border-[var(--teal-border)]
                          px-3.5 py-1.5 rounded-full mb-5">
            ✦ Start your free store
          </div>
          <h1 className="font-display font-extrabold text-[2.9rem] leading-[1.08] tracking-tight
                         text-[var(--ink)] mb-4">
            Set up your<br/>
            <span className="text-[var(--teal)] relative">
              smart store.
              <span className="absolute left-0 -bottom-0.5 right-0 h-[3px] rounded-full"
                    style={{ background: 'linear-gradient(90deg,var(--teal-mid),transparent)' }} />
            </span>
          </h1>
          <p className="text-[0.95rem] text-[var(--muted)] leading-[1.75] mb-9">
            Register as a store manager. Add your inventory, and our XGBoost ML model starts predicting demand for your specific products immediately.
          </p>

          {/* Steps indicator */}
          <div className="flex flex-col gap-4">
            {[
              { n:1, title:'Create account',   desc:'Name, email & password' },
              { n:2, title:'Store details',    desc:'Store name & location'  },
              { n:3, title:'Add inventory',    desc:'Manual, photo or file'  },
            ].map((s) => (
              <div key={s.n} className="flex items-center gap-4">
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-[0.8rem] font-bold flex-shrink-0
                                 ${step >= s.n
                                   ? 'text-white'
                                   : 'border-2 border-[var(--border)] text-[var(--muted)]'}`}
                     style={step >= s.n ? { background:'linear-gradient(135deg,var(--teal),var(--teal-lt))' } : {}}>
                  {step > s.n ? '✓' : s.n}
                </div>
                <div>
                  <p className={`text-[0.85rem] font-semibold ${step >= s.n ? 'text-[var(--ink)]' : 'text-[var(--muted)]'}`}>
                    {s.title}
                  </p>
                  <p className="text-[0.74rem] text-[var(--muted)]">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* RIGHT FORM PANEL */}
      <div className="w-[480px] bg-white border-l border-[var(--border)] flex flex-col justify-center
                      px-11 py-14 relative z-10"
           style={{ boxShadow: '-8px 0 48px rgba(13,148,136,0.06)' }}>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-6">
          {[1,2].map((s) => (
            <div key={s} className={`h-1.5 rounded-full transition-all duration-300 ${
              step >= s ? 'bg-[var(--teal)]' : 'bg-[var(--border)]'
            } ${s === step ? 'flex-[2]' : 'flex-1'}`} />
          ))}
        </div>

        {step === 1 ? (
          <>
            <p className="text-[0.7rem] font-extrabold tracking-widest uppercase text-[var(--teal)] mb-2">
              Step 1 of 2
            </p>
            <h2 className="font-display font-bold text-[2rem] text-[var(--ink)] tracking-tight mb-1.5">
              Create your account
            </h2>
            <p className="text-[0.88rem] text-[var(--muted)] mb-8">
              You'll be the store manager. Cashier accounts are created by you after setup.
            </p>

            <form onSubmit={handleNext} className="flex flex-col gap-5">
              <Input label="Full name"       type="text"     value={form.name}     onChange={set('name')}     placeholder="Your name"         icon="👤" required />
              <Input label="Email address"   type="email"    value={form.email}    onChange={set('email')}    placeholder="you@store.com"     icon="✉️" required />
              <Input label="Password"        type="password" value={form.password} onChange={set('password')} placeholder="Min 6 characters"  icon="🔒" required />
              <Input label="Confirm password" type="password" value={form.confirm} onChange={set('confirm')}  placeholder="Repeat password"   icon="🔒" required />

              {error && (
                <div className="text-[0.82rem] text-red-600 text-center py-3 px-4 bg-red-50
                                border border-red-200 rounded-[9px] font-medium">
                  ⚠️ {error}
                </div>
              )}

              <Button type="submit" size="lg" className="w-full mt-1">
                Continue →
              </Button>
            </form>
          </>
        ) : (
          <>
            <p className="text-[0.7rem] font-extrabold tracking-widest uppercase text-[var(--teal)] mb-2">
              Step 2 of 2
            </p>
            <h2 className="font-display font-bold text-[2rem] text-[var(--ink)] tracking-tight mb-1.5">
              Your store details
            </h2>
            <p className="text-[0.88rem] text-[var(--muted)] mb-8">
              Tell us about your store. You can update this later in settings.
            </p>

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <Input label="Store name"    type="text" value={form.store_name} onChange={set('store_name')} placeholder="e.g. Sri Varsha Fresh Mart" icon="🏪" required />
              <Input label="Address (optional)" type="text" value={form.address} onChange={set('address')} placeholder="City, State" icon="📍" />

              {error && (
                <div className="text-[0.82rem] text-red-600 text-center py-3 px-4 bg-red-50
                                border border-red-200 rounded-[9px] font-medium">
                  ⚠️ {error}
                </div>
              )}

              <Button type="submit" size="lg" loading={loading} className="w-full mt-1">
                Create store →
              </Button>
              <button type="button" onClick={() => setStep(1)}
                      className="text-[0.85rem] text-[var(--muted)] hover:text-[var(--ink)] bg-transparent border-0 cursor-pointer text-center">
                ← Back
              </button>
            </form>
          </>
        )}

        <p className="text-center text-[0.82rem] text-[var(--muted)] mt-8">
          Already have an account?{' '}
          <Link to="/login" className="text-[var(--teal)] font-semibold hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}