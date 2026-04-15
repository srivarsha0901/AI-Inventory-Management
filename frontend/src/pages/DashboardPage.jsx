import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { dashboardService, inventoryService, seasonalService } from '../services/apiServices'
import { useMLStatus } from '../hooks/useMLStatus'
import KpiCard from '../components/ui/KpiCard'
import Badge from '../components/ui/Badge'
import StockBar from '../components/ui/StockBar'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { Card, CardHeader, CardBody } from '../components/ui/Card'

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
  General:    { bg:'#f3f4f6', color:'#6b7280' },
}
const ALERT_BG = { critical:'#fee2e2', warning:'#fef3c7', success:'#ecfdf5' }
const DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Today']

export default function DashboardPage() {
  const navigate = useNavigate()
  const { hasMLPredictions } = useMLStatus()

  const { data: stats,   loading: loadingStats  } = useApi(dashboardService.getStats)
  const { data: alerts,  loading: loadingAlerts } = useApi(dashboardService.getAlerts)
  const { data: trend,   loading: loadingTrend  } = useApi(() => dashboardService.getSalesTrend('week'))
  const { data: invData, loading: loadingInv    } = useApi(inventoryService.getAll)
  const { data: notifData }                        = useApi(seasonalService.getNotifications)

  const s = stats || {}
  const notifications = notifData?.data || []

  // Real alerts only — no mock
  const al = alerts?.data?.map((a, i) => ({
    id:   a.id || i,
    type: a.severity === 'critical' ? 'critical'
        : a.severity === 'warning'  ? 'warning'
        : 'success',
    icon: a.type === 'expiry'    ? '⏰' : '📦',
    name: `${a.product_name} — ${a.message.split('—')[0]?.trim() || a.message}`,
    meta: a.message,
  })) || []

  // Real inventory only — no mock
  const inv = invData?.data?.map((item, i) => ({
    id:       i,
    emoji:    item.emoji || '📦',
    name:     item.product_name || 'Unknown',
    category: item.category || 'General',
    stock:    `${Math.round(item.stock || 0)} ${item.unit || 'units'}`,
    pct:      item.safety_stock > 0
                ? Math.min(100, Math.round((item.stock / (item.safety_stock * 2)) * 100))
                : item.stock > 0 ? 60 : 0,
    expiry:   'N/A',
    status:   item.stock_status === 'Out of Stock' ? 'critical'
            : item.stock_status === 'Low Stock'    ? 'low'
            : 'healthy',
  })) || []

  // Real sales trend — aggregate by day
  const hasSalesData = trend?.data && trend.data.length > 0

  const salesByDay = (() => {
    if (!hasSalesData) return null
    // Group sales by day of week
    const daySums = [0, 0, 0, 0, 0, 0, 0]
    trend.data.forEach((sale) => {
      const d = new Date(sale.created_at)
      const dow = d.getDay() // 0=Sun
      const idx = dow === 0 ? 6 : dow - 1 // Mon=0 ... Sun=6
      daySums[idx] += sale.total || 0
    })
    return daySums
  })()

  const maxSale    = salesByDay ? Math.max(...salesByDay, 1) : 1
  const totalWeek  = salesByDay ? salesByDay.reduce((a, b) => a + b, 0) : 0
  const avgDay     = salesByDay ? Math.round(totalWeek / 7) : 0
  const peakIdx    = salesByDay ? salesByDay.indexOf(Math.max(...salesByDay)) : -1
  const peakDay    = peakIdx >= 0 ? DAYS[peakIdx] : '—'

  return (
    <div className="space-y-6">

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard
          label="Total Products"
          value={s.total_products || 0}
          icon="📦"
          stripeColor="linear-gradient(90deg,var(--teal),var(--teal-lt))"
          valueColor="var(--teal)"
          meta="In your store"
        />
        <KpiCard
          label="Low Stock Items"
          value={hasMLPredictions ? (s.low_stock_count || 0) : '—'}
          icon="⚠️"
          stripeColor="linear-gradient(90deg,#f59e0b,#fbbf24)"
          valueColor="#f59e0b"
          meta={hasMLPredictions ? "Needs reorder" : "Awaiting sales data"}
        />
        <KpiCard
          label="AI Predictions"
          value={hasMLPredictions ? 'Active' : 'Pending'}
          icon="🤖"
          stripeColor="linear-gradient(90deg,#ef4444,#f87171)"
          valueColor={hasMLPredictions ? '#22c55e' : '#f59e0b'}
          meta={hasMLPredictions ? "Based on your sales" : "Upload sales history"}
        />
        <KpiCard
          label="Today's Revenue"
          value={`₹${(s.revenue_today || 0).toLocaleString('en-IN')}`}
          icon="💰"
          stripeColor="linear-gradient(90deg,#3b82f6,#60a5fa)"
          valueColor="#3b82f6"
          meta="From POS sales today"
        />
      </div>

      {/* AI not active banner */}
      {!hasMLPredictions && (s.total_products > 0) && (
        <div className="bg-amber-50 border border-amber-200 rounded-[14px] px-6 py-5 flex items-start gap-4">
          <span className="text-3xl">🧠</span>
          <div className="flex-1">
            <p className="font-bold text-amber-800 text-[0.95rem]">AI predictions not active yet</p>
            <p className="text-amber-700 text-[0.82rem] mt-1">
              Upload your past sales history to activate forecasting, smart alerts, and reorder suggestions.
              Or start recording sales via POS — predictions activate after enough data is collected.
            </p>
          </div>
          <button
            onClick={() => navigate('/onboarding')}
            className="flex-shrink-0 px-4 py-2 bg-amber-600 text-white text-[0.82rem] font-bold
                       rounded-[9px] hover:bg-amber-700 transition-colors border-0 cursor-pointer">
            Upload Sales →
          </button>
        </div>
      )}

      {/* Alerts + Sales Chart */}
      <div className="grid grid-cols-2 gap-4">

        {/* Alerts */}
        <Card>
          <CardHeader
            title="Active Alerts"
            icon="⚡"
            right={
              al.filter(a => a.type === 'critical').length > 0
                ? <Badge variant="red">{al.filter(a => a.type === 'critical').length} critical</Badge>
                : <Badge variant="teal">All clear</Badge>
            }
          />
          {loadingAlerts ? <LoadingSpinner /> : (
            al.length === 0 ? (
              <div className="px-5 py-10 text-center text-[var(--muted)] text-sm">
                ✅ No active alerts. Everything looks good!
              </div>
            ) : (
              <div>
                {al.slice(0, 5).map((a) => (
                  <div key={a.id}
                       className="flex items-start gap-3 px-5 py-3.5 border-b border-[var(--border)]
                                  last:border-0 hover:bg-[var(--cream)] transition-colors">
                    <div className="w-9 h-9 rounded-[9px] flex items-center justify-center text-base flex-shrink-0"
                         style={{ background: ALERT_BG[a.type] || '#f3f4f6' }}>
                      {a.icon}
                    </div>
                    <div>
                      <p className="font-semibold text-[0.85rem] text-[var(--ink)]">{a.name}</p>
                      <p className="text-[0.74rem] text-[var(--muted)] mt-0.5">{a.meta}</p>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </Card>

        {/* Sales chart */}
        <Card>
          <CardHeader
            title="Sales — Last 7 Days"
            icon="📈"
            right={
              hasSalesData
                ? <Badge variant="teal">₹{totalWeek.toLocaleString('en-IN')} this week</Badge>
                : <Badge variant="amber">No sales yet</Badge>
            }
          />
          <div className="px-5 pt-5">
            {!hasSalesData ? (
              <div className="flex flex-col items-center justify-center py-10 text-center gap-2">
                <span className="text-3xl">📊</span>
                <p className="font-semibold text-[var(--ink)] text-[0.9rem]">No sales recorded yet</p>
                <p className="text-[0.78rem] text-[var(--muted)]">
                  Start billing via POS to see your sales trend here.
                </p>
                <button
                  onClick={() => navigate('/pos')}
                  className="mt-2 text-[0.82rem] text-[var(--teal)] font-semibold hover:underline
                             bg-transparent border-0 cursor-pointer">
                  Go to POS →
                </button>
              </div>
            ) : (
              <>
                <div className="flex items-end gap-2 h-24">
                  {DAYS.map((day, i) => {
                    const val       = salesByDay[i] || 0
                    const heightPct = (val / maxSale) * 100
                    const isToday   = i === 6
                    return (
                      <div key={day} className="flex-1 flex flex-col items-center gap-1.5 h-full">
                        <div className="w-full flex-1 flex items-end">
                          <div
                            className="w-full rounded-t-[6px] transition-all"
                            style={{
                              height: `${Math.max(heightPct, val > 0 ? 5 : 0)}%`,
                              background: isToday
                                ? 'linear-gradient(180deg,var(--teal),var(--teal-lt))'
                                : 'linear-gradient(180deg,var(--teal-mid),#a7f3d0)',
                              opacity: isToday ? 1 : 0.6,
                            }}
                          />
                        </div>
                        <span className={`text-[0.64rem] font-semibold ${isToday ? 'text-[var(--teal)]' : 'text-[var(--muted)]'}`}>
                          {day}
                        </span>
                      </div>
                    )
                  })}
                </div>

                <div className="grid grid-cols-3 border-t border-[var(--border)] mt-4">
                  {[
                    { label:'Avg / Day',    value: `₹${avgDay.toLocaleString('en-IN')}` },
                    { label:'Peak Day',     value: peakDay, color:'var(--teal)' },
                    { label:'Weekly Total', value: `₹${totalWeek.toLocaleString('en-IN')}` },
                  ].map((stat, i) => (
                    <div key={stat.label}
                         className={`text-center py-3.5 ${i < 2 ? 'border-r border-[var(--border)]' : ''}`}>
                      <p className="text-[0.68rem] font-bold uppercase tracking-wider text-[var(--muted)] mb-1">
                        {stat.label}
                      </p>
                      <p className="font-display font-bold text-[1rem]"
                         style={{ color: stat.color || 'var(--ink)' }}>
                        {stat.value}
                      </p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </Card>
      </div>

      {/* Seasonal Notifications */}
      {notifications.length > 0 && (
        <Card>
          <CardHeader title="Smart Notifications" icon="🔔"
            right={<Badge variant="teal">{notifications.length} active</Badge>}
          />
          <div>
            {notifications.map((n, i) => {
              const bgMap = {
                festival: '#fef3c7', festival_upcoming: '#eff6ff',
                seasonal_suggestion: '#ecfdf5', perishable_warning: '#fee2e2',
              }
              return (
                <div key={i}
                     className="flex items-start gap-3 px-5 py-4 border-b border-[var(--border)]
                                last:border-0 hover:bg-[var(--cream)] transition-colors">
                  <div className="w-9 h-9 rounded-[9px] flex items-center justify-center text-lg flex-shrink-0"
                       style={{ background: bgMap[n.type] || '#f3f4f6' }}>
                    {n.icon}
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-[0.88rem] text-[var(--ink)]">{n.title}</p>
                    <p className="text-[0.78rem] text-[var(--muted)] mt-0.5 leading-relaxed">{n.message}</p>
                  </div>
                  {n.action && (
                    <button
                      onClick={() => {
                        if (n.action === 'View Suggestions') navigate('/analytics')
                        // Festival boost would need more logic
                      }}
                      className="flex-shrink-0 text-[0.76rem] font-bold text-[var(--teal)] hover:underline
                                 bg-transparent border-0 cursor-pointer mt-1">
                      {n.action} →
                    </button>
                  )}
                  <Badge variant={n.priority === 'high' ? 'red' : 'amber'} >
                    {n.priority}
                  </Badge>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {/* Inventory snapshot */}
      <div>
        <div className="flex items-end justify-between mb-4">
          <div>
            <h2 className="font-display font-bold text-[1.1rem] text-[var(--ink)]">Inventory Snapshot</h2>
            <p className="text-[0.78rem] text-[var(--muted)] mt-0.5">Real-time stock levels for your products</p>
          </div>
          <button onClick={() => navigate('/inventory')}
                  className="text-[0.78rem] text-[var(--teal)] font-semibold hover:underline
                             bg-transparent border-0 cursor-pointer">
            View all →
          </button>
        </div>

        <Card>
          {loadingInv ? <LoadingSpinner /> : (
            inv.length === 0 ? (
              <div className="px-5 py-10 text-center text-[var(--muted)] text-sm">
                No inventory yet. Add products during onboarding.
              </div>
            ) : (
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    {['Product','Category','Stock','Level','Status'].map((h) => (
                      <th key={h}
                          className="px-5 py-2.5 text-left text-[0.68rem] font-extrabold tracking-widest
                                     uppercase text-[var(--muted)] border-b border-[var(--border)] bg-[var(--cream)]">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {inv.map((item) => {
                    const st  = STATUS_MAP[item.status] || STATUS_MAP.healthy
                    const cat = CAT_COLORS[item.category] || CAT_COLORS.General
                    return (
                      <tr key={item.id}
                          className="border-b border-[var(--border)] last:border-0
                                     hover:bg-[var(--teal-pale)] transition-colors">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 bg-[var(--cream)] border border-[var(--border)]
                                            rounded-[8px] flex items-center justify-center text-base flex-shrink-0">
                              {item.emoji}
                            </div>
                            <span className="font-semibold text-[0.85rem] text-[var(--ink)]">{item.name}</span>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className="text-[0.7rem] font-bold px-2.5 py-1 rounded-full"
                                style={{ background: cat.bg, color: cat.color }}>
                            {item.category}
                          </span>
                        </td>
                        <td className="px-5 py-3 font-bold text-[0.85rem] text-[var(--ink)]">{item.stock}</td>
                        <td className="px-5 py-3"><StockBar pct={item.pct} /></td>
                        <td className="px-5 py-3">
                          <Badge variant={st.variant}>{st.label}</Badge>
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
    </div>
  )
}