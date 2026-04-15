import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authService } from '../services/apiServices'
import Input  from '../components/ui/Input'
import Button from '../components/ui/Button'

export default function LoginPage() {
  const { login }    = useAuth()
  const navigate     = useNavigate()

  const [role,     setRole]     = useState('manager')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleRoleSwitch = (r) => {
    setRole(r)
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authService.login({ email, password, role })
      login(res.data.user, res.data.token)
      navigate(res.data.user.role === 'manager' ? '/dashboard' : '/pos', { replace: true })
    } catch (err) {
      setError(err.response?.data?.message || 'Invalid credentials. Please try again.')
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

      {/* LEFT BRANDING PANEL */}
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
            ✦ AI-Powered Inventory Intelligence
          </div>
          <h1 className="font-display font-extrabold text-[2.9rem] leading-[1.08] tracking-tight
                         text-[var(--ink)] mb-4">
            Smarter stock,<br/>
            <span className="text-[var(--teal)] relative">
              less waste.
              <span className="absolute left-0 -bottom-0.5 right-0 h-[3px] rounded-full"
                    style={{ background: 'linear-gradient(90deg,var(--teal-mid),transparent)' }} />
            </span>
          </h1>
          <p className="text-[0.95rem] text-[var(--muted)] leading-[1.75] mb-9">
            Predict demand with XGBoost ML, prevent stock-outs, scan invoices with OCR,
            and manage perishables — all in one place.
          </p>

          <div className="grid grid-cols-3 gap-3 mb-9">
            {[
              { num: '34%', lbl: 'Avg. waste\nreduction'  },
              { num: '98%', lbl: 'Stock-out\nprevention'  },
              { num: 'ML',  lbl: 'XGBoost\nforecasting'   },
            ].map((s, i) => (
              <div key={i}
                   className="bg-white border border-[var(--border)] rounded-[14px] p-4 text-center animate-rise"
                   style={{ animationDelay: `${i * 0.1}s`, boxShadow: 'var(--shadow-sm)' }}>
                <div className="font-display font-bold text-[1.6rem] text-[var(--teal)] leading-none">{s.num}</div>
                <div className="text-[0.68rem] text-[var(--muted)] mt-1 leading-snug font-medium whitespace-pre-line">{s.lbl}</div>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap gap-2">
            {['📦 POS Billing','📊 Forecasting','🔁 Reorder Engine','🧾 OCR Invoices','⚠️ Expiry Alerts','📈 Analytics'].map((m) => (
              <span key={m}
                    className="text-[0.73rem] font-semibold px-3 py-1.5 rounded-full bg-white
                               border border-[var(--border)] text-[var(--muted)] hover:border-[var(--teal)]
                               hover:text-[var(--teal)] hover:bg-[var(--teal-pale)] transition-all cursor-default"
                    style={{ boxShadow: 'var(--shadow-sm)' }}>
                {m}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* RIGHT FORM PANEL */}
      <div className="w-[480px] bg-white border-l border-[var(--border)] flex flex-col justify-center
                      px-11 py-14 relative z-10"
           style={{ boxShadow: '-8px 0 48px rgba(13,148,136,0.06)' }}>

        <p className="text-[0.7rem] font-extrabold tracking-widest uppercase text-[var(--teal)] mb-2">
          Welcome back
        </p>
        <h2 className="font-display font-bold text-[2rem] text-[var(--ink)] tracking-tight mb-1.5">
          Sign in to your workspace
        </h2>
        <p className="text-[0.88rem] text-[var(--muted)] mb-8">
          Choose your role and enter your credentials below.
        </p>

        {/* Role toggle */}
        <div className="flex bg-[var(--cream)] border border-[var(--border)] rounded-[12px] p-1 gap-1 mb-7">
          {['manager','cashier'].map((r) => (
            <button
              key={r}
              onClick={() => handleRoleSwitch(r)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-[9px] text-[0.85rem]
                          font-semibold transition-all duration-200 border-0 cursor-pointer
                          ${role === r
                            ? 'bg-white text-[var(--teal)] shadow-md'
                            : 'bg-transparent text-[var(--muted)] hover:text-[var(--ink)]'}`}
              style={role === r ? { boxShadow: 'var(--shadow-md)' } : {}}
            >
              {r === 'manager' ? '🏢' : '💳'}
              <span className="capitalize">{r}</span>
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <Input
            label="Email address"
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@yourstore.com"
            icon="✉️"
            required
          />
          <Input
            label="Password"
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            icon="🔒"
            required
          />

          <div className="flex justify-between items-center text-[0.82rem]">
            <label className="flex items-center gap-2 text-[var(--muted)] cursor-pointer font-medium">
              <input type="checkbox" defaultChecked className="accent-[var(--teal)]" />
              Remember me
            </label>
          </div>

          {error && (
            <div className="text-[0.82rem] text-red-600 text-center py-3 px-4 bg-red-50
                            border border-red-200 rounded-[9px] font-medium">
              ⚠️ {error}
            </div>
          )}

          <Button type="submit" size="lg" loading={loading} className="w-full mt-1">
            Sign in →
          </Button>
        </form>

        <p className="text-center text-[0.82rem] text-[var(--muted)] mt-6">
          New store?{' '}
          <Link to="/register" className="text-[var(--teal)] font-semibold hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}