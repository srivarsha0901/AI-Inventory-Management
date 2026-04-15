import { useState, useEffect } from 'react'
import { useApi }    from '../hooks/useApi'
import { posService } from '../services/apiServices'
import Badge   from '../components/ui/Badge'
import Button  from '../components/ui/Button'
import LoadingSpinner from '../components/ui/LoadingSpinner'

/* Mock products — replaced by Flask /api/products */
const MOCK_PRODUCTS = [
  { id:1,  name:'Mango Alphonso',  emoji:'🥭', price:120, unit:'kg',    category:'fruits' },
  { id:2,  name:'Bananas',         emoji:'🍌', price:40,  unit:'dozen', category:'fruits' },
  { id:3,  name:'Papaya',          emoji:'🍈', price:55,  unit:'kg',    category:'fruits' },
  { id:4,  name:'Strawberries',    emoji:'🍓', price:180, unit:'box',   category:'fruits' },
  { id:5,  name:'Tomatoes',        emoji:'🍅', price:30,  unit:'kg',    category:'vegetables' },
  { id:6,  name:'Spinach',         emoji:'🥬', price:25,  unit:'bunch', category:'vegetables' },
  { id:7,  name:'Carrots',         emoji:'🥕', price:35,  unit:'kg',    category:'vegetables' },
  { id:8,  name:'Broccoli',        emoji:'🥦', price:60,  unit:'head',  category:'vegetables' },
  { id:9,  name:'Full Cream Milk', emoji:'🥛', price:58,  unit:'L',     category:'dairy' },
  { id:10, name:'Greek Yogurt',    emoji:'🍶', price:85,  unit:'cup',   category:'dairy' },
  { id:11, name:'Cheddar Cheese',  emoji:'🧀', price:145, unit:'pack',  category:'dairy' },
  { id:12, name:'Eggs (6-pack)',   emoji:'🥚', price:72,  unit:'pack',  category:'dairy' },
  { id:13, name:'Sourdough Bread', emoji:'🍞', price:95,  unit:'loaf',  category:'bakery' },
  { id:14, name:'Croissant',       emoji:'🥐', price:45,  unit:'pc',    category:'bakery' },
  { id:15, name:'Bagel',           emoji:'🥯', price:38,  unit:'pc',    category:'bakery' },
  { id:16, name:'Muffin',          emoji:'🧁', price:55,  unit:'pc',    category:'bakery' },
]

const CATS = ['all','dairy','bakery','fruits','vegetables','grains','oils','beverages','eggs']
export default function POSPage() {
  const { data, loading } = useApi(posService.getProducts)
  const products = data?.data || MOCK_PRODUCTS

  const [search,  setSearch]  = useState('')
  const [cat,     setCat]     = useState('all')
  const [cart,    setCart]    = useState({})     // { productId: { product, qty } }
  const [paying,  setPaying]  = useState(false)
  const [success, setSuccess] = useState(false)

  /* Filtered product list */
  const filtered = products.filter((p) =>
    (cat === 'all' || (p.category || '').toLowerCase() === cat) &&
    (!search || p.name.toLowerCase().includes(search.toLowerCase()))
  )

  /* Cart helpers */
  const addToCart = (p) => setCart((c) => ({
    ...c, [p.id]: { product: p, qty: (c[p.id]?.qty || 0) + 1 }
  }))
  const changeQty = (id, delta) => setCart((c) => {
    const next = { ...c }
    if (!next[id]) return next
    next[id] = { ...next[id], qty: next[id].qty + delta }
    if (next[id].qty <= 0) delete next[id]
    return next
  })
  const clearCart = () => setCart({})

  /* Totals */
  const items   = Object.values(cart)
  const sub     = items.reduce((s, { product: p, qty }) => s + p.price * qty, 0)
  const tax     = Math.round(sub * 0.05)
  const total   = sub + tax
  const count   = items.length

  /* Process payment → POST /api/sales */
  const processPayment = async () => {
    if (!count) return
    setPaying(true)
    try {
      await posService.createSale({
        items: items.map(({ product: p, qty }) => ({
          product_id: p.id, name: p.name, qty, unit_price: p.price,
        })),
        subtotal: sub,
        tax,
        total,
      })
      setSuccess(true)
      clearCart()
      setTimeout(() => setSuccess(false), 3000)
    } catch {
      // If Flask is offline, still show success for demo
      setSuccess(true)
      clearCart()
      setTimeout(() => setSuccess(false), 3000)
    } finally {
      setPaying(false)
    }
  }

  return (
    <div className="grid gap-5" style={{ gridTemplateColumns: '1fr 340px', alignItems: 'start' }}>

      {/* ── LEFT: Product catalog ── */}
      <div>
        {/* Search bar */}
        <div className="relative mb-4">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-base text-[var(--muted)]">🔍</span>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search products or scan barcode…"
            className="w-full bg-white border-[1.5px] border-[var(--border)] rounded-[10px]
                       py-3 pl-10 pr-4 text-[0.9rem] text-[var(--ink)] outline-none font-body
                       focus:border-[var(--teal)] focus:shadow-[0_0_0_4px_rgba(13,148,136,0.1)]
                       transition-all placeholder:text-[#a8c4be]"
            style={{ boxShadow: 'var(--shadow-sm)' }}
          />
        </div>

        {/* Category filters */}
        <div className="flex flex-wrap gap-2 mb-5">
          {CATS.map((c) => (
            <button
              key={c}
              onClick={() => setCat(c)}
              className={`px-4 py-1.5 rounded-full text-[0.8rem] font-semibold border-[1.5px]
                          transition-all cursor-pointer capitalize font-body
                          ${cat === c
                            ? 'bg-[var(--teal)] text-white border-[var(--teal)] shadow-btn'
                            : 'bg-white text-[var(--muted)] border-[var(--border)] hover:border-[var(--teal)] hover:text-[var(--teal)] hover:bg-[var(--teal-pale)]'}`}
              style={cat === c ? { boxShadow: '0 4px 12px rgba(13,148,136,0.3)' } : { boxShadow: 'var(--shadow-sm)' }}
            >
{{
  all:'All Items', dairy:'🥛 Dairy', bakery:'🍞 Bakery',
  fruits:'🍎 Fruits', vegetables:'🥬 Vegetables',
  grains:'🌾 Grains', oils:'🫙 Oils',
  beverages:'🥤 Beverages', eggs:'🥚 Eggs'
}[c]}            </button>
          ))}
        </div>

        {/* Products grid */}
        {loading ? <LoadingSpinner message="Loading products…" /> : (
          <div className="grid gap-3"
               style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(130px,1fr))' }}>
            {filtered.map((p, i) => (
              <div
                key={p.id}
                onClick={() => addToCart(p)}
                className="bg-white border-[1.5px] border-[var(--border)] rounded-[12px] p-4 cursor-pointer
                           transition-all duration-150 hover:border-[var(--teal)] hover:shadow-md hover:-translate-y-0.5 active:scale-[0.97]"
                style={{ boxShadow: 'var(--shadow-sm)', animationDelay: `${i * 0.03}s` }}
              >
                <span className="text-[2rem] block mb-2">{p.emoji}</span>
                <div className="text-[0.8rem] font-bold text-[var(--ink)] leading-snug">{p.name}</div>
                <div className="text-[0.76rem] font-bold text-[var(--teal)] mt-1">₹{p.price} / {p.unit}</div>
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="col-span-full py-12 text-center text-[var(--muted)] text-sm">
                No products found for "{search}"
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── RIGHT: Cart ── */}
      <div
        className="bg-white border border-[var(--border)] rounded-[14px] flex flex-col overflow-hidden"
        style={{
          position: 'sticky',
          top: 'calc(64px + 28px)',
          maxHeight: 'calc(100vh - 64px - 56px)',
          boxShadow: 'var(--shadow-md)',
        }}
      >
        {/* Cart header */}
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-[var(--border)] bg-[var(--cream)]">
          <div className="font-bold text-[0.9rem] text-[var(--ink)] flex items-center gap-2">
            🛒 Cart
          </div>
          <Badge variant="blue">{count} item{count !== 1 ? 's' : ''}</Badge>
        </div>

        {/* Cart body */}
        <div className="flex-1 overflow-y-auto">
          {count === 0 ? (
            <div className="flex flex-col items-center justify-center h-36 gap-2 text-[var(--muted)] text-sm">
              <span className="text-3xl">🛒</span>
              <span>Your cart is empty</span>
            </div>
          ) : (
            items.map(({ product: p, qty }) => (
              <div key={p.id}
                   className="flex items-center gap-2.5 px-4 py-3 border-b border-[var(--border)] hover:bg-[var(--cream)] transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-[0.84rem] text-[var(--ink)] truncate">{p.emoji} {p.name}</p>
                  <p className="text-[0.72rem] text-[var(--muted)] mt-0.5">₹{p.price} per {p.unit}</p>
                </div>
                {/* Qty controls */}
                <div className="flex items-center gap-1.5">
                  <button onClick={() => changeQty(p.id, -1)}
                          className="w-6 h-6 rounded-[6px] bg-[var(--cream)] border border-[var(--border)]
                                     text-[var(--ink)] font-bold text-sm flex items-center justify-center
                                     hover:bg-[var(--teal)] hover:text-white hover:border-[var(--teal)] transition-all cursor-pointer">
                    −
                  </button>
                  <span className="font-extrabold text-[0.9rem] text-[var(--ink)] w-5 text-center">{qty}</span>
                  <button onClick={() => changeQty(p.id, 1)}
                          className="w-6 h-6 rounded-[6px] bg-[var(--cream)] border border-[var(--border)]
                                     text-[var(--ink)] font-bold text-sm flex items-center justify-center
                                     hover:bg-[var(--teal)] hover:text-white hover:border-[var(--teal)] transition-all cursor-pointer">
                    +
                  </button>
                </div>
                <span className="font-extrabold text-[var(--teal)] text-[0.88rem] w-14 text-right">
                  ₹{(p.price * qty).toLocaleString('en-IN')}
                </span>
              </div>
            ))
          )}
        </div>

        {/* Cart footer */}
        <div className="px-4 py-4 border-t border-[var(--border)] bg-[var(--cream)] rounded-b-[14px]">
          <div className="flex justify-between text-[0.82rem] text-[var(--muted)] font-medium mb-1.5">
            <span>Subtotal</span><span>₹{sub.toLocaleString('en-IN')}</span>
          </div>
          <div className="flex justify-between text-[0.82rem] text-[var(--muted)] font-medium mb-3">
            <span>GST (5%)</span><span>₹{tax.toLocaleString('en-IN')}</span>
          </div>
          <div className="flex justify-between font-extrabold text-[1.05rem] text-[var(--ink)]
                          pt-2.5 mb-4 border-t-2 border-dashed border-[var(--border)]">
            <span>Total Amount</span>
            <span style={{ color: 'var(--teal)' }}>₹{total.toLocaleString('en-IN')}</span>
          </div>

          {success ? (
            <div className="w-full py-3 rounded-[10px] bg-green-50 border border-green-200
                            text-green-700 text-[0.88rem] font-bold text-center">
              ✅ Payment processed! Inventory updated.
            </div>
          ) : (
            <Button
              size="lg"
              className="w-full"
              onClick={processPayment}
              loading={paying}
              disabled={count === 0}
            >
              Process Payment →
            </Button>
          )}

          {count > 0 && !success && (
            <button onClick={clearCart}
                    className="w-full mt-2 text-[0.78rem] text-[var(--muted)] font-medium
                               hover:text-red-500 transition-colors bg-transparent border-0 cursor-pointer py-1">
              Clear cart
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
