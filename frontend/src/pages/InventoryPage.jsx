import { useState } from 'react'
import { useApi }           from '../hooks/useApi'
import { inventoryService } from '../services/apiServices'
import { Card, CardHeader } from '../components/ui/Card'
import Badge          from '../components/ui/Badge'
import StockBar       from '../components/ui/StockBar'
import Button         from '../components/ui/Button'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import api            from '../services/api'

const STATUS_MAP = {
  critical: { variant:'red',   label:'Critical' },
  expiring: { variant:'red',   label:'Expiring' },
  low:      { variant:'amber', label:'Low'      },
  healthy:  { variant:'teal',  label:'Healthy'  },
}

const CAT_COLORS = {
  Dairy:      { bg:'#eff6ff', color:'#3b82f6' },
  Fruits:     { bg:'#fef3c7', color:'#d97706' },
  Bakery:     { bg:'#fdf4ff', color:'#a21caf' },
  Vegetables: { bg:'var(--teal-pale)', color:'var(--teal)' },
  Grains:     { bg:'#fef9c3', color:'#ca8a04' },
  Oils:       { bg:'#fdf2f8', color:'#db2777' },
  Beverages:  { bg:'#ecfdf5', color:'#059669' },
  Eggs:       { bg:'#fff7ed', color:'#ea580c' },
  Snacks:     { bg:'#f5f3ff', color:'#7c3aed' },
  General:    { bg:'#f3f4f6', color:'#6b7280' },
}

export default function InventoryPage() {
  const { data, loading, refetch } = useApi(inventoryService.getAll)

  const [search,      setSearch]      = useState('')
  const [catFilter,   setCatFilter]   = useState('all')
  const [statusFilter,setStatus]      = useState('all')
  const [editItem,    setEditItem]    = useState(null)
  const [editValues,  setEditValues]  = useState({})
  const [saving,      setSaving]      = useState(false)

  const inventory = data?.data?.map((item) => ({
    id:       item.id,
    emoji:    item.emoji || '📦',
    name:     item.product_name || 'Unknown',
    category: item.category || 'General',
    stock:    Math.round(item.stock || 0),
    unit:     item.unit || 'units',
    pct:      item.safety_stock > 0
                ? Math.min(100, Math.round((item.stock / (item.safety_stock * 2)) * 100))
                : item.stock > 0 ? 60 : 0,
    expiry:       'N/A',
    reorder:      Math.round(item.reorder_point || item.safety_stock || 0),
    safety_stock: Math.round(item.safety_stock || 0),
    status:   item.stock_status === 'Out of Stock' ? 'critical'
            : item.stock_status === 'Low Stock'    ? 'low'
            : 'healthy',
  })) || []

  const categories = ['all', ...new Set(inventory.map(i => i.category))]
  const statuses   = ['all','healthy','low','critical']

  const filtered = inventory.filter((item) => {
    const matchSearch = !search || item.name.toLowerCase().includes(search.toLowerCase())
    const matchCat    = catFilter === 'all' || item.category === catFilter
    const matchStatus = statusFilter === 'all' || item.status === statusFilter
    return matchSearch && matchCat && matchStatus
  })

  const handleEdit = (item) => {
    setEditItem(item.id)
    setEditValues({ stock: item.stock, reorder_point: item.reorder })
  }

  const handleSave = async (item) => {
    setSaving(true)
    try {
      await api.put(`/inventory/${item.id}`, {
        stock:         parseInt(editValues.stock),
        reorder_point: parseInt(editValues.reorder_point),
        safety_stock:  item.safety_stock,
      })
      refetch()
      setEditItem(null)
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to save')
    } finally { setSaving(false) }
  }

  const handleRemove = async (item) => {
    if (!window.confirm(`Remove "${item.name}" from inventory?`)) return
    try {
      await api.delete(`/inventory/${item.id}`)
      refetch()
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to remove')
    }
  }

  return (
    <div className="space-y-5">

      {/* Summary */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label:'Total Items',   value: inventory.length,                                                    color:'var(--teal)' },
          { label:'Low Stock',     value: inventory.filter(i=>i.status==='low'||i.status==='critical').length, color:'#f59e0b'     },
          { label:'Expiring Soon', value: inventory.filter(i=>i.status==='expiring').length,                   color:'#ef4444'     },
          { label:'Healthy Stock', value: inventory.filter(i=>i.status==='healthy').length,                    color:'#22c55e'     },
        ].map((s) => (
          <div key={s.label}
               className="bg-white border border-[var(--border)] rounded-[12px] px-5 py-4"
               style={{ boxShadow:'var(--shadow-sm)' }}>
            <p className="text-[0.7rem] font-extrabold uppercase tracking-widest text-[var(--muted)] mb-1">
              {s.label}
            </p>
            <p className="font-display font-bold text-[1.8rem]" style={{ color:s.color }}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-center gap-3 px-5 py-4">
          <div className="relative flex-1 min-w-[200px]">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm">🔍</span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search products…"
              className="w-full pl-9 pr-3 py-2 bg-[var(--cream)] border border-[var(--border)]
                         rounded-[9px] text-[0.88rem] outline-none focus:border-[var(--teal)] transition-all"
            />
          </div>

          <select value={catFilter} onChange={(e) => setCatFilter(e.target.value)}
                  className="px-3 py-2 bg-[var(--cream)] border border-[var(--border)] rounded-[9px]
                             text-[0.85rem] outline-none cursor-pointer focus:border-[var(--teal)]">
            {categories.map((c) => (
              <option key={c} value={c}>
                {c === 'all' ? 'All Categories' : c}
              </option>
            ))}
          </select>

          <select value={statusFilter} onChange={(e) => setStatus(e.target.value)}
                  className="px-3 py-2 bg-[var(--cream)] border border-[var(--border)] rounded-[9px]
                             text-[0.85rem] outline-none cursor-pointer focus:border-[var(--teal)]">
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s === 'all' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>

          <Button variant="outline" size="sm" onClick={refetch}>↻ Refresh</Button>
        </div>
      </Card>

      {/* Table */}
      <Card>
        <CardHeader
          title={`All Products (${filtered.length})`}
          icon="📦"
          right={<Badge variant="teal">Live</Badge>}
        />
        {loading ? <LoadingSpinner /> : (
          filtered.length === 0 ? (
            <div className="px-5 py-12 text-center text-[var(--muted)] text-sm">
              No products match your filters.
            </div>
          ) : (
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {['Product','Category','Stock','Level','Reorder Point','Status','Actions'].map((h) => (
                    <th key={h}
                        className="px-5 py-3 text-left text-[0.67rem] font-extrabold tracking-widest
                                   uppercase text-[var(--muted)] border-b border-[var(--border)] bg-[var(--cream)]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const st  = STATUS_MAP[item.status] || STATUS_MAP.healthy
                  const cat = CAT_COLORS[item.category] || CAT_COLORS.General
                  const isEditing = editItem === item.id
                  return (
                    <tr key={item.id}
                        className={`border-b border-[var(--border)] last:border-0 transition-colors
                                    ${isEditing ? 'bg-[var(--teal-pale)]' : 'hover:bg-[var(--teal-pale)]'}`}>

                      {/* Product */}
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 bg-[var(--cream)] border border-[var(--border)]
                                          rounded-[8px] flex items-center justify-center text-base flex-shrink-0">
                            {item.emoji}
                          </div>
                          <span className="font-semibold text-[0.85rem] text-[var(--ink)]">{item.name}</span>
                        </div>
                      </td>

                      {/* Category */}
                      <td className="px-5 py-3">
                        <span className="text-[0.7rem] font-bold px-2.5 py-1 rounded-full"
                              style={{ background:cat.bg, color:cat.color }}>
                          {item.category}
                        </span>
                      </td>

                      {/* Stock — editable */}
                      <td className="px-5 py-3">
                        {isEditing ? (
                          <input
                            type="number"
                            value={editValues.stock}
                            onChange={e => setEditValues(p => ({ ...p, stock: e.target.value }))}
                            className="w-20 text-[0.85rem] border border-[var(--teal)] rounded-[6px]
                                       px-2 py-1 bg-white outline-none"
                          />
                        ) : (
                          <span className="font-bold text-[0.85rem] text-[var(--ink)]">
                            {item.stock} {item.unit}
                          </span>
                        )}
                      </td>

                      {/* Level bar */}
                      <td className="px-5 py-3"><StockBar pct={item.pct} width={90} /></td>

                      {/* Reorder point — editable */}
                      <td className="px-5 py-3">
                        {isEditing ? (
                          <input
                            type="number"
                            value={editValues.reorder_point}
                            onChange={e => setEditValues(p => ({ ...p, reorder_point: e.target.value }))}
                            className="w-20 text-[0.85rem] border border-[var(--teal)] rounded-[6px]
                                       px-2 py-1 bg-white outline-none"
                          />
                        ) : (
                          <span className="text-[0.84rem] text-[var(--muted)] font-medium">
                            {item.reorder} {item.unit}
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="px-5 py-3">
                        <Badge variant={st.variant}>{st.label}</Badge>
                      </td>

                      {/* Actions */}
                      <td className="px-5 py-3">
                        {isEditing ? (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleSave(item)}
                              disabled={saving}
                              className="text-[0.74rem] text-white bg-[var(--teal)] px-3 py-1.5
                                         rounded-[6px] border-0 cursor-pointer font-semibold hover:opacity-90">
                              {saving ? '...' : 'Save'}
                            </button>
                            <button
                              onClick={() => setEditItem(null)}
                              className="text-[0.74rem] text-[var(--muted)] hover:text-[var(--ink)]
                                         bg-transparent border-0 cursor-pointer">
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleEdit(item)}
                              className="text-[0.74rem] text-[var(--teal)] font-semibold hover:underline
                                         bg-transparent border-0 cursor-pointer">
                              Edit
                            </button>
                            <button
                              onClick={() => handleRemove(item)}
                              className="text-[0.74rem] text-red-400 font-semibold hover:underline
                                         bg-transparent border-0 cursor-pointer">
                              Remove
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )
        )}
      </Card>
    </div>
  )
}