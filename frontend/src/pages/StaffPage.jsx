import { useState } from 'react'
import { useApi }   from '../hooks/useApi'
import { staffService } from '../services/apiServices'
import { Card, CardHeader } from '../components/ui/Card'
import Badge   from '../components/ui/Badge'
import Button  from '../components/ui/Button'
import Input   from '../components/ui/Input'
import LoadingSpinner from '../components/ui/LoadingSpinner'

const ACTION_ICONS = {
  sale_created:     { icon:'💰', color:'#22c55e' },
  stock_reduced:    { icon:'📦', color:'#f59e0b' },
  staff_created:    { icon:'👤', color:'#3b82f6' },
  staff_deactivated:{ icon:'🚫', color:'#ef4444' },
  inventory_updated:{ icon:'✏️', color:'var(--teal)' },
}

export default function StaffPage() {
  const { data: staffData, loading: staffLoading, refetch } = useApi(staffService.getAll)
  const { data: activityData, loading: actLoading }         = useApi(staffService.getActivity)

  const staff    = staffData?.data    || []
  const activity = activityData?.data || []

  const [showForm, setShowForm] = useState(false)
  const [form,     setForm]     = useState({ name:'', email:'', password:'' })
  const [error,    setError]    = useState('')
  const [saving,   setSaving]   = useState(false)
  const [selected, setSelected] = useState(null) // selected staff for drill-down

  const set = (k) => (e) => setForm(p => ({ ...p, [k]: e.target.value }))

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.name || !form.email || !form.password)
      return setError('All fields required')
    setSaving(true); setError('')
    try {
      await staffService.create(form)
      setForm({ name:'', email:'', password:'' })
      setShowForm(false)
      refetch()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create staff')
    } finally { setSaving(false) }
  }

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display font-bold text-[1.3rem] text-[var(--ink)]">Staff Management</h2>
          <p className="text-[0.82rem] text-[var(--muted)] mt-0.5">
            Manage your salesmen and track their activity
          </p>
        </div>
        <Button size="md" onClick={() => setShowForm(p => !p)}>
          {showForm ? '✕ Cancel' : '+ Add Salesman'}
        </Button>
      </div>

      {/* Create form */}
      {showForm && (
        <Card>
          <CardHeader title="New Salesman Account" icon="👤" />
          <div className="p-5">
            <form onSubmit={handleCreate} className="grid grid-cols-3 gap-4">
              <Input label="Full Name"  value={form.name}     onChange={set('name')}     placeholder="e.g. Ravi Kumar"       icon="👤" />
              <Input label="Email"      value={form.email}    onChange={set('email')}    placeholder="ravi@yourstore.com"    icon="✉️" type="email" />
              <Input label="Password"   value={form.password} onChange={set('password')} placeholder="Temporary password"    icon="🔒" type="password" />
              {error && (
                <div className="col-span-3 text-[0.82rem] text-red-600 py-2 px-3 bg-red-50 border border-red-200 rounded-[9px]">
                  ⚠️ {error}
                </div>
              )}
              <div className="col-span-3 flex gap-3">
                <Button type="submit" loading={saving}>Create Salesman</Button>
                <button type="button" onClick={() => setShowForm(false)}
                        className="text-[0.85rem] text-[var(--muted)] hover:text-[var(--ink)] bg-transparent border-0 cursor-pointer">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </Card>
      )}

      {/* Staff list */}
      <Card>
        <CardHeader title={`Salesmen (${staff.length})`} icon="👥"
                    right={<Badge variant="teal">Your Store</Badge>} />
        {staffLoading ? <LoadingSpinner /> : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {['Name','Email','Total Sales','Last Login','Status','Action'].map(h => (
                  <th key={h} className="px-5 py-3 text-left text-[0.67rem] font-extrabold tracking-widest
                                         uppercase text-[var(--muted)] border-b border-[var(--border)] bg-[var(--cream)]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {staff.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-[var(--muted)] text-sm">
                    No salesmen yet. Add your first salesman above.
                  </td>
                </tr>
              )}
              {staff.map(s => (
                <tr key={s.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--teal-pale)] transition-colors">
                  <td className="px-5 py-3 font-semibold text-[0.85rem] text-[var(--ink)]">
                    👤 {s.name}
                  </td>
                  <td className="px-5 py-3 text-[0.85rem] text-[var(--muted)]">{s.email}</td>
                  <td className="px-5 py-3 font-bold text-[0.85rem] text-[var(--teal)]">
                    {s.total_sales} sales
                  </td>
                  <td className="px-5 py-3 text-[0.82rem] text-[var(--muted)]">
                    {s.last_login ? new Date(s.last_login).toLocaleDateString('en-IN') : 'Never'}
                  </td>
                  <td className="px-5 py-3">
                    <Badge variant={s.is_active ? 'teal' : 'red'}>
                      {s.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </td>
                  <td className="px-5 py-3">
                    <button onClick={() => setSelected(selected?.id === s.id ? null : s)}
                            className="text-[0.74rem] text-[var(--teal)] font-semibold hover:underline
                                       bg-transparent border-0 cursor-pointer mr-3">
                      View Sales
                    </button>
                    {s.is_active && (
                      <button onClick={async () => {
                                await staffService.deactivate(s.id); refetch()
                              }}
                              className="text-[0.74rem] text-red-400 font-semibold hover:underline
                                         bg-transparent border-0 cursor-pointer">
                        Deactivate
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Drill-down: selected staff sales */}
      {selected && <StaffSalesPanel staff={selected} />}

      {/* Activity log */}
      <Card>
        <CardHeader title="Activity Log" icon="📋"
                    right={<Badge variant="blue">Live</Badge>} />
        {actLoading ? <LoadingSpinner /> : (
          <div>
            {activity.length === 0 && (
              <p className="px-5 py-8 text-center text-[var(--muted)] text-sm">
                No activity recorded yet.
              </p>
            )}
            {activity.map(a => {
              const style = ACTION_ICONS[a.action] || { icon:'📝', color:'var(--muted)' }
              return (
                <div key={a.id}
                     className="flex items-start gap-3 px-5 py-3.5 border-b border-[var(--border)]
                                last:border-0 hover:bg-[var(--cream)] transition-colors">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0"
                       style={{ background: style.color + '20' }}>
                    {style.icon}
                  </div>
                  <div className="flex-1">
                    <p className="text-[0.85rem] font-semibold text-[var(--ink)]">{a.detail}</p>
                    <p className="text-[0.74rem] text-[var(--muted)] mt-0.5">by {a.user_name}</p>
                  </div>
                  <span className="text-[0.72rem] text-[var(--muted)] flex-shrink-0">
                    {new Date(a.created_at).toLocaleString('en-IN', {
                      day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'
                    })}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}

function StaffSalesPanel({ staff }) {
  const { data, loading } = useApi(staffService.getSales, staff.id, [staff.id])
  const sales = data?.data || []

  return (
    <Card>
      <CardHeader title={`Sales by ${staff.name}`} icon="💰"
                  right={<Badge variant="teal">{sales.length} transactions</Badge>} />
      {loading ? <LoadingSpinner /> : (
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {['Date','Items','Subtotal','GST','Total'].map(h => (
                <th key={h} className="px-5 py-3 text-left text-[0.67rem] font-extrabold tracking-widest
                                       uppercase text-[var(--muted)] border-b border-[var(--border)] bg-[var(--cream)]">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sales.length === 0 && (
              <tr>
                <td colSpan={5} className="px-5 py-8 text-center text-[var(--muted)] text-sm">
                  No sales recorded yet.
                </td>
              </tr>
            )}
            {sales.map(s => (
              <tr key={s.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--teal-pale)]">
                <td className="px-5 py-3 text-[0.82rem] text-[var(--muted)]">
                  {new Date(s.created_at).toLocaleString('en-IN', {
                    day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit'
                  })}
                </td>
                <td className="px-5 py-3 text-[0.85rem] text-[var(--ink)]">
                  {s.items?.length || 0} items
                </td>
                <td className="px-5 py-3 text-[0.85rem] text-[var(--ink)]">₹{s.subtotal?.toLocaleString('en-IN')}</td>
                <td className="px-5 py-3 text-[0.85rem] text-[var(--muted)]">₹{s.tax?.toLocaleString('en-IN')}</td>
                <td className="px-5 py-3 font-bold text-[var(--teal)]">₹{s.total?.toLocaleString('en-IN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  )
}