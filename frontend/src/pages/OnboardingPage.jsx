import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Button from '../components/ui/Button'
import api    from '../services/api'

const CATEGORIES = [
  'Dairy','Bakery','Fruits','Vegetables','Grains','Oils',
  'Beverages','Eggs','Snacks','Spices','Pulses',
  'Condiments','Household','Sweeteners','General','Other'
]

const EMPTY_ITEM = {
  name:'', category:'Other', unit:'kg',
  cost_price:'', selling_price:'', shelf_life_days:'',
  stock:'', safety_stock:'', restock_days:'7', emoji:'📦'
}

export default function OnboardingPage({ startStep = 1 }) {
  const { user, login } = useAuth()
  const navigate        = useNavigate()
  const location        = useLocation()

  const isUploadSalesRoute = location.pathname === '/upload-sales'
  const initialStep        = isUploadSalesRoute ? 3 : startStep

  const [step,           setStep]           = useState(initialStep)
  const [items,          setItems]          = useState([{ ...EMPTY_ITEM }])
  const [loading,        setLoading]        = useState(false)
  const [error,          setError]          = useState('')
  const [fileProcessing, setFileProcessing] = useState(false)
  const [salesUploaded,  setSalesUploaded]  = useState(false)

  useEffect(() => {
    setStep(isUploadSalesRoute ? 3 : 1)
  }, [location.pathname])

  const updateItem = (i, k, v) =>
    setItems(prev => prev.map((it, idx) => idx === i ? { ...it, [k]: v } : it))
  const addRow    = () => setItems(p => [...p, { ...EMPTY_ITEM }])
  const removeRow = (i) => setItems(p => p.filter((_, idx) => idx !== i))

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setFileProcessing(true); setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post('/onboarding/parse-file', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (res.data.items?.length) {
        setItems(res.data.items.map(it => ({
          ...EMPTY_ITEM,
          ...it,
          category: CATEGORIES.includes(it.category) ? it.category : 'Other',
          shelf_life_days: it.shelf_life_days || '',
        })))
        setStep(2)
      }
    } catch { setError('Could not parse file. Please try manual entry.') }
    finally  { setFileProcessing(false) }
  }

  const handlePhotoUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setFileProcessing(true); setError('')
    try {
      const fd = new FormData()
      fd.append('image', file)
      const res = await api.post('/onboarding/parse-photo', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      if (res.data.items?.length) {
        setItems(res.data.items.map(it => ({
          ...EMPTY_ITEM,
          ...it,
          category: CATEGORIES.includes(it.category) ? it.category : 'Other',
          shelf_life_days: it.shelf_life_days || '',
        })))
        setStep(2)
      }
    } catch { setError('Could not extract from photo. Please try manual entry.') }
    finally  { setFileProcessing(false) }
  }

  const handleSubmitInventory = async () => {
    const valid = items.filter(it => it.name.trim())
    if (!valid.length) return setError('Add at least one product.')
    setLoading(true); setError('')
    try {
      await api.post('/onboarding/inventory', { items: valid })
      setStep(3)
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to save inventory.')
    } finally { setLoading(false) }
  }

  const handleSalesUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setFileProcessing(true); setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      await api.post('/onboarding/parse-sales', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000, // sales history imports can take longer for larger files
      })
      setSalesUploaded(true)
    } catch (err) {
      if (err.code === 'ECONNABORTED') {
        setError('Upload is taking longer than expected. Please try a smaller file or retry.')
      } else {
        setError(err.response?.data?.message || 'Could not parse sales file. You can skip this step.')
      }
    }
    finally  { setFileProcessing(false) }
  }

  const handleFinish = async () => {
    setLoading(true)
    try {
      await api.post('/auth/onboarding-complete')
      login({ ...user, onboarding_complete: true })
    } catch {}
    finally { setLoading(false) }
    if (isUploadSalesRoute) {
      navigate('/dashboard', { replace: true })
    } else {
      setStep(4)
    }
  }

  const Logo = () => (
    <div className="flex items-center gap-3 mb-8">
      <div className="w-10 h-10 rounded-[12px] flex items-center justify-center text-[1.2rem]"
           style={{ background:'linear-gradient(135deg,var(--teal),var(--teal-lt))' }}>🌿</div>
      <span className="font-display font-bold text-[1.3rem] text-[var(--ink)]">
        Fresh<span className="text-[var(--teal)]">Track</span>
      </span>
    </div>
  )

  if (step === 1) return (
    <div className="min-h-screen bg-[var(--cream)] flex items-center justify-center p-6">
      <div className="max-w-[640px] w-full">
        <Logo />
        <div className="bg-white border border-[var(--border)] rounded-[20px] p-10"
             style={{ boxShadow:'var(--shadow-md)' }}>
          <div className="flex items-center gap-2 mb-6">
            {['Account','Store','Inventory','Sales History','Done'].map((s, i) => (
              <div key={s} className="flex items-center gap-1">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[0.65rem] font-bold
                                ${i <= 2 ? 'bg-[var(--teal)] text-white' : 'bg-[var(--border)] text-[var(--muted)]'}`}>
                  {i < 2 ? '✓' : i + 1}
                </div>
                {i < 4 && <div className={`h-0.5 w-8 ${i < 2 ? 'bg-[var(--teal)]' : 'bg-[var(--border)]'}`} />}
              </div>
            ))}
          </div>

          <div className="inline-flex items-center gap-1.5 text-[0.7rem] font-bold tracking-widest uppercase
                          text-[var(--teal)] bg-[var(--teal-pale)] border border-[var(--teal-border)]
                          px-3 py-1 rounded-full mb-4">
            Step 3 of 5 — Add Inventory
          </div>
          <h2 className="font-display font-bold text-[1.8rem] text-[var(--ink)] mb-2">
            Add your initial inventory
          </h2>
          <p className="text-[0.9rem] text-[var(--muted)] mb-8">
            Welcome, <strong>{user?.name}</strong>! Add the products your store carries.
          </p>

          <div className="grid grid-cols-3 gap-4">
            <button onClick={() => setStep(2)}
                    className="p-6 rounded-[16px] border-2 border-[var(--border)] hover:border-[var(--teal)]
                               text-left transition-all cursor-pointer bg-white">
              <div className="text-2xl mb-3">✏️</div>
              <p className="font-bold text-[0.9rem] text-[var(--ink)] mb-1">Manual entry</p>
              <p className="text-[0.76rem] text-[var(--muted)] leading-snug">Type product names and stock levels one by one</p>
            </button>

            <label className="p-6 rounded-[16px] border-2 border-[var(--border)] hover:border-[var(--teal)]
                              text-left transition-all cursor-pointer bg-white block">
              <div className="text-2xl mb-3">📄</div>
              <p className="font-bold text-[0.9rem] text-[var(--ink)] mb-1">Upload file</p>
              <p className="text-[0.76rem] text-[var(--muted)] leading-snug">CSV or Excel with your product list</p>
              <p className="text-[0.7rem] text-[var(--teal)] mt-1 font-semibold">
                Format: name, category, unit, cost_price, selling_price, shelf_life_days, stock, safety_stock, restock_days
              </p>
              <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleFileUpload} />
            </label>

            <label className="p-6 rounded-[16px] border-2 border-[var(--border)] hover:border-[var(--teal)]
                              text-left transition-all cursor-pointer bg-white block">
              <div className="text-2xl mb-3">📷</div>
              <p className="font-bold text-[0.9rem] text-[var(--ink)] mb-1">Scan a photo</p>
              <p className="text-[0.76rem] text-[var(--muted)] leading-snug">Photo of your stock list or invoice</p>
              <input type="file" accept="image/*" className="hidden" onChange={handlePhotoUpload} />
            </label>
          </div>

          {fileProcessing && (
            <div className="mt-6 text-center text-[0.88rem] text-[var(--teal)] font-semibold animate-pulse">
              ⏳ Processing your file...
            </div>
          )}
          {error && (
            <div className="mt-4 text-[0.82rem] text-red-600 text-center py-3 px-4 bg-red-50
                            border border-red-200 rounded-[9px]">⚠️ {error}</div>
          )}
        </div>
      </div>
    </div>
  )

  if (step === 2) return (
    <div className="min-h-screen bg-[var(--cream)] p-6">
      <div className="max-w-[1100px] mx-auto">
        <Logo />
        <div className="bg-white border border-[var(--border)] rounded-[20px] p-8"
             style={{ boxShadow:'var(--shadow-md)' }}>

          <div className="inline-flex items-center gap-1.5 text-[0.7rem] font-bold tracking-widest uppercase
                          text-[var(--teal)] bg-[var(--teal-pale)] border border-[var(--teal-border)]
                          px-3 py-1 rounded-full mb-4">
            Step 3 of 5 — Review Inventory
          </div>
          <h2 className="font-display font-bold text-[1.5rem] text-[var(--ink)] mb-1">
            Review your inventory
          </h2>
          <p className="text-[0.88rem] text-[var(--muted)] mb-2">
            Add or edit products below.
          </p>
          <div className="text-[0.78rem] text-[var(--muted)] mb-6 bg-[var(--teal-pale)] border border-[var(--teal-border)]
                        px-4 py-3 rounded-[8px] space-y-1">
            <p>💡 <strong>CP</strong> = Cost Price (what you pay) &nbsp;|&nbsp; <strong>SP</strong> = Selling Price (what customers pay)</p>
            <p>🕐 <strong>Shelf Life</strong> — how many days the product stays fresh. Dairy: 3-7 &nbsp;|&nbsp; Bakery: 2-5 &nbsp;|&nbsp; Fruits: 5-10 &nbsp;|&nbsp; Grains: 90-365</p>
            <p>📦 <strong>Restock Days</strong> — how often you reorder. Should be ≤ shelf life!</p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {['Emoji','Product Name','Category','Unit','CP (₹)','SP (₹)','Shelf Life','Stock','Safety Stock','Restock Days',''].map(h => (
                    <th key={h} className="px-3 py-2 text-left text-[0.67rem] font-extrabold tracking-widest
                                           uppercase text-[var(--muted)] border-b border-[var(--border)] bg-[var(--cream)]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr key={i} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-3 py-2">
                      <input value={item.emoji} onChange={e => updateItem(i,'emoji',e.target.value)}
                             className="w-12 text-center text-xl bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] py-1 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.name} onChange={e => updateItem(i,'name',e.target.value)}
                             placeholder="e.g. Full Cream Milk"
                             className="w-full text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] px-3 py-2 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <select value={item.category} onChange={e => updateItem(i,'category',e.target.value)}
                              className="text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                         rounded-[8px] px-2 py-2 outline-none focus:border-[var(--teal)]">
                        {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.unit} onChange={e => updateItem(i,'unit',e.target.value)}
                             placeholder="kg"
                             className="w-16 text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] px-2 py-2 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.cost_price} onChange={e => updateItem(i,'cost_price',e.target.value)}
                             placeholder="CP" type="number"
                             className="w-16 text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] px-2 py-2 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.selling_price} onChange={e => updateItem(i,'selling_price',e.target.value)}
                             placeholder="SP" type="number"
                             className="w-16 text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] px-2 py-2 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.shelf_life_days} onChange={e => updateItem(i,'shelf_life_days',e.target.value)}
                             placeholder="days" type="number" min="1"
                             className="w-16 text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] px-2 py-2 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.stock} onChange={e => updateItem(i,'stock',e.target.value)}
                             placeholder="0" type="number"
                             className="w-20 text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] px-2 py-2 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.safety_stock} onChange={e => updateItem(i,'safety_stock',e.target.value)}
                             placeholder="0" type="number"
                             className="w-20 text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] px-2 py-2 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <input value={item.restock_days || 7}
                             onChange={e => updateItem(i,'restock_days',e.target.value)}
                             placeholder="7" type="number" min="1" max="90"
                             className="w-16 text-[0.85rem] bg-[var(--cream)] border border-[var(--border)]
                                        rounded-[8px] px-2 py-2 outline-none focus:border-[var(--teal)]" />
                    </td>
                    <td className="px-3 py-2">
                      <button onClick={() => removeRow(i)}
                              className="text-red-400 hover:text-red-600 text-lg bg-transparent border-0 cursor-pointer">
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <button onClick={addRow}
                  className="mt-4 text-[0.85rem] text-[var(--teal)] font-semibold hover:underline
                             bg-transparent border-0 cursor-pointer">
            + Add another product
          </button>

          {error && (
            <div className="mt-4 text-[0.82rem] text-red-600 py-3 px-4 bg-red-50
                            border border-red-200 rounded-[9px]">⚠️ {error}</div>
          )}

          <div className="flex gap-3 mt-8">
            <button onClick={() => setStep(1)}
                    className="text-[0.85rem] text-[var(--muted)] hover:text-[var(--ink)]
                               bg-transparent border-0 cursor-pointer">
              ← Back
            </button>
            <Button size="lg" loading={loading} onClick={handleSubmitInventory} className="flex-1">
              Save & Continue →
            </Button>
          </div>
        </div>
      </div>
    </div>
  )

  if (step === 3) return (
    <div className="min-h-screen bg-[var(--cream)] flex items-center justify-center p-6">
      <div className="max-w-[600px] w-full">
        <Logo />
        <div className="bg-white border border-[var(--border)] rounded-[20px] p-10"
             style={{ boxShadow:'var(--shadow-md)' }}>
          <div className="inline-flex items-center gap-1.5 text-[0.7rem] font-bold tracking-widest uppercase
                          text-[var(--teal)] bg-[var(--teal-pale)] border border-[var(--teal-border)]
                          px-3 py-1 rounded-full mb-4">
            {isUploadSalesRoute ? 'Upload Sales History' : 'Step 4 of 5 — Sales History (Optional)'}
          </div>
          <h2 className="font-display font-bold text-[1.8rem] text-[var(--ink)] mb-2">
            Upload past sales history
          </h2>
          <p className="text-[0.9rem] text-[var(--muted)] mb-4 leading-relaxed">
            Our AI needs sales history to predict demand accurately.
            Upload past sales and predictions start <strong>immediately</strong>.
            Without this, predictions activate after <strong>7 days of POS sales</strong>.
          </p>

          <div className="bg-[var(--cream)] border border-[var(--border)] rounded-[12px] p-4 mb-6">
            <p className="font-bold text-[0.82rem] text-[var(--ink)] mb-2">📋 Required CSV format:</p>
            <div className="bg-white border border-[var(--border)] rounded-[8px] px-4 py-3
                            font-mono text-[0.78rem] text-[var(--muted)]">
              date, product_name, qty_sold, unit_price, total
            </div>
            <div className="mt-2 text-[0.75rem] text-[var(--muted)] space-y-0.5">
              <p>• <strong>date</strong> — YYYY-MM-DD (e.g. 2026-03-01)</p>
              <p>• <strong>product_name</strong> — must match inventory product names exactly</p>
              <p>• <strong>qty_sold</strong> — units sold that day</p>
              <p>• <strong>unit_price</strong> — price per unit in ₹</p>
              <p>• <strong>total</strong> — total revenue for that row</p>
            </div>
          </div>

          {!salesUploaded ? (
            <label className="block w-full p-6 border-2 border-dashed border-[var(--teal-border)]
                              rounded-[14px] text-center cursor-pointer hover:border-[var(--teal)]
                              hover:bg-[var(--teal-pale)] transition-all">
              <div className="text-3xl mb-2">📂</div>
              <p className="font-semibold text-[var(--ink)] text-[0.9rem]">Click to upload sales CSV or Excel</p>
              <p className="text-[0.78rem] text-[var(--muted)] mt-1">.csv, .xlsx, .xls supported</p>
              <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleSalesUpload} />
            </label>
          ) : (
            <div className="w-full p-5 bg-green-50 border border-green-200 rounded-[14px] text-center">
              <div className="text-3xl mb-2">✅</div>
              <p className="font-bold text-green-700 text-[0.9rem]">Sales history uploaded!</p>
              <p className="text-green-600 text-[0.8rem] mt-1">
                Go to Forecast page and click "Run Predictions" to activate AI forecasting.
              </p>
            </div>
          )}

          {fileProcessing && (
            <p className="mt-4 text-center text-[var(--teal)] text-[0.88rem] font-semibold animate-pulse">
              ⏳ Importing sales history...
            </p>
          )}
          {error && (
            <p className="mt-4 text-[0.82rem] text-red-600 py-2 px-3 bg-red-50
                          border border-red-200 rounded-[9px]">⚠️ {error}</p>
          )}

          <div className="flex gap-3 mt-6">
            {!isUploadSalesRoute && (
              <button onClick={() => setStep(2)}
                      className="text-[0.85rem] text-[var(--muted)] hover:text-[var(--ink)]
                                 bg-transparent border-0 cursor-pointer">← Back</button>
            )}
            <Button size="lg" loading={loading} onClick={handleFinish} className="flex-1">
              {salesUploaded
                ? (isUploadSalesRoute ? 'Done — Go to Dashboard →' : 'Finish Setup →')
                : (isUploadSalesRoute ? 'Skip for now →' : "Skip — I'll record sales via POS →")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-[var(--cream)] flex items-center justify-center p-6">
      <div className="max-w-[500px] w-full text-center">
        <Logo />
        <div className="text-6xl mb-6">🎉</div>
        <h2 className="font-display font-bold text-[2rem] text-[var(--ink)] mb-3">You're all set!</h2>
        <p className="text-[0.95rem] text-[var(--muted)] mb-8 leading-relaxed">
          Your store is ready. FreshTrack will track inventory, generate alerts,
          and predict demand for your products.
          {salesUploaded && (
            <span> Sales history imported — go to Forecast and click
              <strong> "Run Predictions"</strong> to activate AI forecasting.
            </span>
          )}
        </p>
        <Button size="lg" className="w-full" onClick={() => navigate('/dashboard', { replace: true })}>
          Go to Dashboard →
        </Button>
      </div>
    </div>
  )
}