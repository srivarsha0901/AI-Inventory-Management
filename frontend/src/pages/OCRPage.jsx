import { useState, useRef, useEffect } from 'react'
import { ocrService } from '../services/apiServices'
import { Card, CardHeader, CardBody } from '../components/ui/Card'
import Badge  from '../components/ui/Badge'
import Button from '../components/ui/Button'

const MOCK_EXTRACTED = [
  { id:1, name:'Tomatoes',       qty:50,  unit:'kg',    price:28,  total:1400, confirmed:true },
  { id:2, name:'Full Cream Milk',qty:100, unit:'L',     price:55,  total:5500, confirmed:true },
  { id:3, name:'Sourdough Bread',qty:40,  unit:'loaves',price:90,  total:3600, confirmed:true },
  { id:4, name:'Greek Yogurt',   qty:60,  unit:'cups',  price:80,  total:4800, confirmed:false },
  { id:5, name:'Bananas',        qty:30,  unit:'dozens',price:38,  total:1140, confirmed:true },
]

// ── Manual Entry Component ──
function ManualEntryForm({ items, setItems, onConfirm, saving }) {
  const [name, setName] = useState('')
  const [qty, setQty] = useState('')
  const [unit, setUnit] = useState('kg')
  const [price, setPrice] = useState('')

  const addItem = () => {
    if (!name || !qty || !price) {
      alert('Please fill in all fields')
      return
    }
    const newItem = {
      id: items.length + 1,
      name,
      qty: parseFloat(qty),
      unit,
      price: parseFloat(price),
      total: parseFloat(qty) * parseFloat(price),
      confirmed: true,
    }
    setItems([...items, newItem])
    setName('')
    setQty('')
    setUnit('kg')
    setPrice('')
  }

  const removeItem = (id) => {
    setItems(items.filter(i => i.id !== id))
  }

  return (
    <CardBody className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-[10px] p-4 text-[0.85rem]">
        📋 <strong>No items detected by OCR</strong> — Manually enter your items below
      </div>

      {/* Input form */}
      <div className="grid grid-cols-4 gap-3 border-b border-[var(--border)] pb-4">
        <input 
          type="text" placeholder="Product name" value={name}
          onChange={e => setName(e.target.value)}
          className="px-3 py-2 border border-[var(--border)] rounded-[8px] text-[0.85rem]"
        />
        <input 
          type="number" placeholder="Qty" value={qty}
          onChange={e => setQty(e.target.value)}
          className="px-3 py-2 border border-[var(--border)] rounded-[8px] text-[0.85rem]"
        />
        <select value={unit} onChange={e => setUnit(e.target.value)}
                className="px-3 py-2 border border-[var(--border)] rounded-[8px] text-[0.85rem]">
          <option>kg</option>
          <option>L</option>
          <option>pcs</option>
          <option>dozen</option>
          <option>boxes</option>
          <option>units</option>
        </select>
        <input 
          type="number" placeholder="Price" value={price}
          onChange={e => setPrice(e.target.value)}
          className="px-3 py-2 border border-[var(--border)] rounded-[8px] text-[0.85rem]"
        />
      </div>
      <Button size="sm" onClick={addItem}>+ Add Item</Button>

      {/* Items list */}
      {items.length > 0 && (
        <>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {['Item','Qty','Unit','Price','Total',''].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-[0.67rem] font-bold text-[var(--muted)] border-b">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id} className="border-b hover:bg-[var(--cream)]">
                  <td className="px-3 py-2 text-[0.85rem]">{it.name}</td>
                  <td className="px-3 py-2 text-[0.85rem]">{it.qty}</td>
                  <td className="px-3 py-2 text-[0.85rem]">{it.unit}</td>
                  <td className="px-3 py-2 text-[0.85rem]">₹{it.price}</td>
                  <td className="px-3 py-2 text-[0.85rem] font-bold">₹{it.total.toLocaleString('en-IN')}</td>
                  <td className="px-3 py-2 text-right">
                    <button onClick={() => removeItem(it.id)} className="text-red-500 hover:text-red-700 text-[0.8rem]">✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between">
            <span className="text-[0.85rem]">Total: <strong className="text-[var(--teal)]">₹{items.reduce((s,i)=>s+i.total,0).toLocaleString('en-IN')}</strong></span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setItems([])}>Clear All</Button>
              <Button size="sm" onClick={() => onConfirm()} loading={saving}>Confirm & Update</Button>
            </div>
          </div>
        </>
      )}
    </CardBody>
  )
}

export default function OCRPage() {
  const fileRef = useRef(null)

  const [stage,     setStage]     = useState('upload')   // upload | processing | review | done
  const [dragOver,  setDragOver]  = useState(false)
  const [fileName,  setFileName]  = useState('')
  const [items,     setItems]     = useState([])
  const [saving,    setSaving]    = useState(false)
  const [invoiceId, setInvoiceId] = useState(null)
  const [history,   setHistory]   = useState([])
  const [error,     setError]     = useState('')
  const [mode,      setMode]      = useState('sale')

  const loadHistory = () => {
    return ocrService.getHistory()
      .then(res => {
        const data = res.data?.data || []
        setHistory(data.map((h, i) => ({
          id:       h.id || i,
          date:     h.created_at ? new Date(h.created_at).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' }) : '—',
          supplier: h.supplier || 'Unknown Supplier',
          items:    h.item_count || 0,
          total:    `₹${(h.total_amount || 0).toLocaleString('en-IN')}`,
          status:   h.status || 'pending',
          type:     h.document_type || 'customer_bill',
        })))
      })
      .catch(() => {})
  }

  // Load real history from backend
  useEffect(() => {
    loadHistory()
  }, [stage]) // re-fetch when stage changes (i.e., after confirming)

  const handleFile = async (file) => {
    if (!file) return
    setFileName(file.name)
    setStage('processing')
    setError('')
    const formData = new FormData()
    formData.append('invoice', file)
    formData.append('mode', mode === 'receive' ? 'supplier_invoice' : 'customer_bill')
    try {
      const res = await ocrService.uploadInvoice(formData)
      const extractedItems = res.data?.items || []
      setItems(extractedItems)
      setInvoiceId(res.data?.id || 'latest')
      if (!extractedItems.length) {
        setError(res.data?.message || 'No items were detected. Add them manually below.')
      }
      loadHistory()
    } catch (err) {
      setItems([])
      setInvoiceId('latest')
      setError(err?.response?.data?.message || 'OCR upload failed. Add items manually below.')
    }
    setTimeout(() => setStage('review'), 1500)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const toggleConfirm = (id) =>
    setItems((prev) => prev.map((it) => it.id === id ? { ...it, confirmed: !it.confirmed } : it))

  const handleConfirm = async () => {
    setSaving(true)
    try {
      await ocrService.confirmItems(invoiceId || 'latest', { mode, items: items.filter(i => i.confirmed) })
      loadHistory()
    }
    catch {}
    setTimeout(() => { setSaving(false); setStage('done') }, 1200)
  }

  const reset = () => { setStage('upload'); setFileName(''); setItems([]); setError('') }

  return (
    <div className="space-y-5">

      <div>
        <h2 className="font-display font-bold text-[1.3rem] text-[var(--ink)]">OCR Bill Processor</h2>
        <p className="text-[0.82rem] text-[var(--muted)] mt-0.5">
          Upload a supplier invoice image — AI extracts items and updates inventory automatically
        </p>
      </div>

      <div className="grid grid-cols-2 gap-5 items-start">

        {/* Upload / Processing / Review */}
        <div className="space-y-4">

          {/* Upload zone */}
          {stage === 'upload' && (
            <Card>
              <CardBody>
                <div className="flex gap-2 mb-4">
                  <button
                    type="button"
                    onClick={() => setMode('sale')}
                    className={`px-3 py-2 rounded-[8px] border text-[0.82rem] font-semibold ${mode === 'sale' ? 'bg-[var(--teal)] text-white border-[var(--teal)]' : 'bg-white border-[var(--border)] text-[var(--ink)]'}`}
                  >
                    Customer bill - reduce stock
                  </button>
                  <button
                    type="button"
                    onClick={() => setMode('receive')}
                    className={`px-3 py-2 rounded-[8px] border text-[0.82rem] font-semibold ${mode === 'receive' ? 'bg-[var(--teal)] text-white border-[var(--teal)]' : 'bg-white border-[var(--border)] text-[var(--ink)]'}`}
                  >
                    Supplier invoice - add stock
                  </button>
                </div>
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileRef.current?.click()}
                  className={`border-2 border-dashed rounded-[12px] p-10 text-center cursor-pointer transition-all
                               ${dragOver
                                 ? 'border-[var(--teal)] bg-[var(--teal-pale)]'
                                 : 'border-[var(--teal-border)] bg-[var(--cream)] hover:border-[var(--teal)] hover:bg-[var(--teal-pale)]'}`}
                >
                  <div className="text-4xl mb-3">🧾</div>
                  <p className="font-bold text-[0.95rem] text-[var(--ink)] mb-1">
                    Drop your {mode === 'sale' ? 'customer bill' : 'supplier invoice'} here
                  </p>
                  <p className="text-[0.82rem] text-[var(--muted)] mb-4">
                    Supports JPG, PNG, PDF · Max 10MB
                  </p>
                  <Button size="sm" variant="outline">Browse files</Button>
                  <input
                    ref={fileRef}
                    type="file"
                    accept="image/*,.pdf"
                    className="hidden"
                    onChange={(e) => handleFile(e.target.files[0])}
                  />
                </div>
              </CardBody>
            </Card>
          )}

          {/* Processing */}
          {stage === 'processing' && (
            <Card>
              <CardBody className="py-12 text-center">
                <div className="text-4xl mb-4 animate-pulse">🤖</div>
                <p className="font-bold text-[var(--ink)] mb-1">Extracting invoice data…</p>
                <p className="text-[0.82rem] text-[var(--muted)]">{fileName}</p>
                <div className="mt-5 h-1.5 bg-[var(--cream)] border border-[var(--border)] rounded-full overflow-hidden mx-auto w-48">
                  <div className="h-full bg-[var(--teal)] rounded-full animate-pulse" style={{ width:'70%' }} />
                </div>
              </CardBody>
            </Card>
          )}

          {/* Review extracted items */}
          {(stage === 'review' || stage === 'done') && (
            <Card>
              <CardHeader
                title={stage === 'done' ? '✅ Inventory Updated' : 'Review Extracted Items'}
                icon={stage === 'done' ? '' : '📋'}
                right={
                  stage === 'review'
                    ? <Badge variant="teal">{items.filter(i=>i.confirmed).length}/{items.length} confirmed</Badge>
                    : <Badge variant="teal">Done</Badge>
                }
              />
              {stage === 'done' ? (
                <CardBody className="text-center py-10">
                  <p className="text-[0.9rem] text-[var(--muted)] mb-5">
                    {items.filter(i=>i.confirmed).length} items {mode === 'sale' ? 'sold from inventory' : 'added to inventory'} successfully.
                  </p>
                  <Button variant="outline" onClick={reset}>Process another invoice</Button>
                </CardBody>
              ) : items.length === 0 ? (
                // ── Manual Entry Form (when OCR extraction returns nothing) ──
                <>
                  {error && (
                    <CardBody>
                      <div className="bg-red-50 border border-red-200 rounded-[10px] p-4 text-[0.85rem] text-red-700">
                        {error}
                      </div>
                    </CardBody>
                  )}
                  <ManualEntryForm items={items} setItems={setItems} onConfirm={handleConfirm} saving={saving} />
                </>
              ) : (
                <>
                  <table className="w-full border-collapse">
                    <thead>
                      <tr>
                        {['✓','Item','Qty','Unit Price','Total'].map((h) => (
                          <th key={h} className="px-4 py-2.5 text-left text-[0.67rem] font-extrabold tracking-widest
                                                 uppercase text-[var(--muted)] border-b border-[var(--border)] bg-[var(--cream)]">
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((it) => (
                        <tr key={it.id}
                            className={`border-b border-[var(--border)] last:border-0 transition-colors
                                        ${it.confirmed ? 'hover:bg-[var(--teal-pale)]' : 'opacity-50 hover:bg-red-50'}`}>
                          <td className="px-4 py-3">
                            <input type="checkbox" checked={it.confirmed}
                                   onChange={() => toggleConfirm(it.id)}
                                   className="accent-[var(--teal)] w-4 h-4 cursor-pointer" />
                          </td>
                          <td className="px-4 py-3 font-semibold text-[0.85rem] text-[var(--ink)]">{it.name}</td>
                          <td className="px-4 py-3 text-[0.85rem]">{it.qty} {it.unit}</td>
                          <td className="px-4 py-3 text-[0.85rem]">₹{it.price}</td>
                          <td className="px-4 py-3 font-bold text-[0.85rem] text-[var(--teal)]">₹{it.total.toLocaleString('en-IN')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--border)] bg-[var(--cream)]">
                    <span className="text-[0.82rem] text-[var(--muted)] font-medium">
                      Total: <strong className="text-[var(--ink)]">
                        ₹{items.filter(i=>i.confirmed).reduce((s,i)=>s+i.total,0).toLocaleString('en-IN')}
                      </strong>
                    </span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" onClick={reset}>Cancel</Button>
                      <Button size="sm" onClick={handleConfirm} loading={saving}>
                        {mode === 'sale' ? 'Confirm Sale & Reduce Stock' : 'Confirm & Add Stock'}
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </Card>
          )}
        </div>

        {/* Upload history */}
        <Card>
          <CardHeader title="Recent Invoices" icon="📂" />
          <div>
            {history.map((h, i) => (
              <div key={h.id}
                   className={`flex items-start gap-3 px-5 py-4 transition-colors hover:bg-[var(--cream)]
                                ${i < history.length - 1 ? 'border-b border-[var(--border)]' : ''}`}>
                <div className="w-9 h-9 rounded-[9px] bg-[var(--teal-pale)] border border-[var(--teal-border)]
                                flex items-center justify-center text-base flex-shrink-0">
                  🧾
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-[0.85rem] text-[var(--ink)]">{h.supplier}</p>
                  <p className="text-[0.74rem] text-[var(--muted)] mt-0.5">{h.date} · {h.items} items · {h.total}</p>
                </div>
                <Badge variant="teal">✓ {h.status}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
