import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { dashboardService, forecastService } from '../services/apiServices'
import { useMLStatus } from '../hooks/useMLStatus'
import { Card, CardHeader, CardBody } from '../components/ui/Card'
import Badge  from '../components/ui/Badge'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import WaitingForData from '../components/ui/WaitingForData'

const CAT_COLORS = {
  Dairy:      { bg:'#eff6ff', color:'#3b82f6', bar:'#3b82f6' },
  Fruits:     { bg:'#fef3c7', color:'#d97706', bar:'#f59e0b' },
  Bakery:     { bg:'#fdf4ff', color:'#a21caf', bar:'#a855f7' },
  Vegetables: { bg:'var(--teal-pale)', color:'var(--teal)', bar:'#0d9488' },
  Grains:     { bg:'#fef3c7', color:'#92400e', bar:'#b45309' },
  Beverages:  { bg:'#ecfdf5', color:'#059669', bar:'#10b981' },
  Oils:       { bg:'#fff7ed', color:'#c2410c', bar:'#ea580c' },
  Eggs:       { bg:'#fef2f2', color:'#dc2626', bar:'#ef4444' },
  General:    { bg:'#f3f4f6', color:'#6b7280', bar:'#9ca3af' },
}

const DAYS = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']

export default function AnalyticsPage() {
  const { hasInventory, hasSalesData, hasMLPredictions } = useMLStatus()
  const [period, setPeriod] = useState('week')

  const { data: stats,    loading: loadingStats }  = useApi(dashboardService.getStats)
  const { data: topData,  loading: loadingTop }     = useApi(dashboardService.getTopProducts)
  const { data: trend,    loading: loadingTrend }   = useApi(() => dashboardService.getSalesTrend(period), null, [period])
  const { data: accuracy, loading: loadingAccuracy } = useApi(forecastService.getAccuracy)

  const s = stats || {}
  const topProducts = topData?.data || []
  const sales = trend?.data || []
  const accuracyData = accuracy?.data || []
  const avgAccuracy  = accuracy?.avg_accuracy || 0

  if (!hasInventory) return (
    <WaitingForData
      icon="📦"
      title="Add your inventory first"
      message="Analytics require products and sales data to generate insights."
      actionLabel="Add Inventory →"
      actionTo="/onboarding"
    />
  )

  // Build sales by day
  const salesByDay = (() => {
    const daySums = [0, 0, 0, 0, 0, 0, 0]
    sales.forEach((sale) => {
      const d = new Date(sale.created_at)
      const dow = d.getDay()
      const idx = dow === 0 ? 6 : dow - 1
      daySums[idx] += sale.total || 0
    })
    return daySums
  })()

  const maxSale   = Math.max(...salesByDay, 1)
  const totalWeek = salesByDay.reduce((a, b) => a + b, 0)
  const avgDay    = Math.round(totalWeek / 7)

  // Category breakdown from top products
  const categoryMap = {}
  topProducts.forEach(p => {
    const cat = 'General'
    categoryMap[cat] = (categoryMap[cat] || 0) + (p.total_revenue || 0)
  })

  const maxTopRevenue = Math.max(...topProducts.map(p => p.total_revenue), 1)

  return (
    <div className="space-y-5">

      {/* Header */}
      <div>
        <h2 className="font-display font-bold text-[1.3rem] text-[var(--ink)]">Analytics Suite</h2>
        <p className="text-[0.82rem] text-[var(--muted)] mt-0.5">
          Deep-dive into sales, forecasts, and product performance
        </p>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label:'Total Revenue',     value:`₹${(s.revenue_today || 0).toLocaleString('en-IN')}`, sub:'Today',                icon:'💰', color:'#0d9488' },
          { label:'Total Sales',       value: s.total_sales || 0,                                  sub:'All time',             icon:'🧾', color:'#3b82f6' },
          { label:'Products Tracked',  value: s.total_products || 0,                               sub:'In your store',        icon:'📦', color:'#f59e0b' },
          { label:'Forecast Accuracy', value: hasMLPredictions ? `${avgAccuracy}%` : '—',          sub: hasMLPredictions ? 'Based on actual sales' : 'Need more data', icon:'🎯', color:'#8b5cf6' },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-white border border-[var(--border)] rounded-[12px] px-5 py-4"
               style={{ boxShadow:'var(--shadow-sm)' }}>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[0.7rem] font-extrabold uppercase tracking-widest text-[var(--muted)]">{kpi.label}</p>
              <span className="text-lg">{kpi.icon}</span>
            </div>
            <p className="font-display font-bold text-[1.6rem] leading-none" style={{ color:kpi.color }}>{kpi.value}</p>
            <p className="text-[0.72rem] text-[var(--muted)] mt-1">{kpi.sub}</p>
          </div>
        ))}
      </div>

      {/* Sales Trend + Top Products */}
      <div className="grid grid-cols-2 gap-4">

        {/* Sales Trend Chart */}
        <Card>
          <CardHeader title="Sales Trend" icon="📈"
            right={
              <div className="flex gap-1">
                {['week','month'].map(p => (
                  <button key={p} onClick={() => setPeriod(p)}
                    className={`text-[0.7rem] font-bold px-2.5 py-1 rounded-full border transition-all cursor-pointer
                               ${period === p
                                 ? 'bg-[var(--teal)] text-white border-[var(--teal)]'
                                 : 'bg-[var(--cream)] text-[var(--muted)] border-[var(--border)] hover:border-[var(--teal)]'}`}>
                    {p === 'week' ? '7 Days' : '30 Days'}
                  </button>
                ))}
              </div>
            }
          />
          <CardBody>
            {loadingTrend ? <LoadingSpinner /> : (
              sales.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center gap-2">
                  <span className="text-3xl">📊</span>
                  <p className="font-semibold text-[var(--ink)] text-[0.9rem]">No sales recorded yet</p>
                  <p className="text-[0.78rem] text-[var(--muted)]">Start billing via POS to see trends here.</p>
                </div>
              ) : (
                <>
                  <div className="flex items-end gap-2 h-32">
                    {DAYS.map((day, i) => {
                      const val       = salesByDay[i] || 0
                      const heightPct = (val / maxSale) * 100
                      const isMax     = val === Math.max(...salesByDay)
                      return (
                        <div key={day} className="flex-1 flex flex-col items-center gap-1.5 h-full group relative">
                          <div className="w-full flex-1 flex items-end">
                            <div
                              className="w-full rounded-t-[6px] transition-all group-hover:opacity-100"
                              style={{
                                height: `${Math.max(heightPct, val > 0 ? 5 : 0)}%`,
                                background: isMax
                                  ? 'linear-gradient(180deg,var(--teal),var(--teal-lt))'
                                  : 'linear-gradient(180deg,var(--teal-mid),#a7f3d0)',
                                opacity: isMax ? 1 : 0.5,
                              }}
                            />
                          </div>
                          {/* Tooltip */}
                          <div className="absolute -top-6 bg-[var(--ink)] text-white text-[0.6rem] px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                            ₹{val.toLocaleString('en-IN')}
                          </div>
                          <span className={`text-[0.64rem] font-semibold ${isMax ? 'text-[var(--teal)]' : 'text-[var(--muted)]'}`}>
                            {day}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                  <div className="grid grid-cols-3 border-t border-[var(--border)] mt-4">
                    {[
                      { label:'Avg / Day',    value: `₹${avgDay.toLocaleString('en-IN')}` },
                      { label:'Total',        value: `₹${totalWeek.toLocaleString('en-IN')}`, color:'var(--teal)' },
                      { label:'Transactions', value: sales.length },
                    ].map((stat, i) => (
                      <div key={stat.label} className={`text-center py-3.5 ${i < 2 ? 'border-r border-[var(--border)]' : ''}`}>
                        <p className="text-[0.68rem] font-bold uppercase tracking-wider text-[var(--muted)] mb-1">{stat.label}</p>
                        <p className="font-display font-bold text-[1rem]" style={{ color: stat.color || 'var(--ink)' }}>{stat.value}</p>
                      </div>
                    ))}
                  </div>
                </>
              )
            )}
          </CardBody>
        </Card>

        {/* Top Products */}
        <Card>
          <CardHeader title="Top Selling Products" icon="🏆"
            right={<Badge variant="teal">By Revenue</Badge>}
          />
          {loadingTop ? <LoadingSpinner /> : (
            topProducts.length === 0 ? (
              <div className="px-5 py-10 text-center text-[var(--muted)] text-sm">
                No sales data available yet.
              </div>
            ) : (
              <div className="px-5 py-4 space-y-3">
                {topProducts.slice(0, 7).map((p, i) => (
                  <div key={p.product_name} className="flex items-center gap-3">
                    <span className="text-[0.7rem] font-extrabold text-[var(--muted)] w-5">{i + 1}</span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[0.85rem] font-semibold text-[var(--ink)]">{p.product_name}</span>
                        <span className="text-[0.78rem] font-bold text-[var(--teal)]">₹{p.total_revenue.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="h-1.5 bg-[var(--cream)] border border-[var(--border)] rounded-full overflow-hidden">
                        <div className="h-full rounded-full transition-all"
                             style={{
                               width: `${(p.total_revenue / maxTopRevenue) * 100}%`,
                               background: i < 3
                                 ? 'linear-gradient(90deg, var(--teal), var(--teal-lt))'
                                 : 'linear-gradient(90deg, var(--teal-mid), #a7f3d0)',
                             }} />
                      </div>
                      <p className="text-[0.68rem] text-[var(--muted)] mt-0.5">{p.sale_count} sales · {p.total_qty} units</p>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </Card>
      </div>

      {/* Forecast Accuracy */}
      {hasMLPredictions && (
        <Card>
          <CardHeader title="Forecast vs Actual" icon="🎯"
            right={<Badge variant={avgAccuracy >= 70 ? 'teal' : 'amber'}>{avgAccuracy}% avg accuracy</Badge>}
          />
          {loadingAccuracy ? <LoadingSpinner /> : (
            accuracyData.length === 0 ? (
              <div className="px-5 py-10 text-center text-[var(--muted)] text-sm">
                Need more sales data to calculate accuracy. Keep recording sales via POS!
              </div>
            ) : (
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    {['Product','Predicted (Daily)','Actual (Daily)','Accuracy','Days of Data'].map(h => (
                      <th key={h} className="px-5 py-3 text-left text-[0.67rem] font-extrabold tracking-widest
                                             uppercase text-[var(--muted)] border-b border-[var(--border)] bg-[var(--cream)]">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {accuracyData.map((a) => (
                    <tr key={a.product_name} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--teal-pale)] transition-colors">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{a.emoji}</span>
                          <span className="font-semibold text-[0.85rem] text-[var(--ink)]">{a.product_name}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3 font-bold text-[0.85rem] text-[var(--ink)]">{a.predicted_daily} units</td>
                      <td className="px-5 py-3 font-bold text-[0.85rem] text-[var(--ink)]">{a.actual_daily} units</td>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-[var(--cream)] border border-[var(--border)] rounded-full h-1.5 w-20 overflow-hidden">
                            <div className="h-full rounded-full transition-all"
                                 style={{
                                   width: `${a.accuracy_pct}%`,
                                   background: a.accuracy_pct >= 80 ? 'var(--teal)' : a.accuracy_pct >= 60 ? '#f59e0b' : '#ef4444',
                                 }} />
                          </div>
                          <span className="text-[0.78rem] font-bold"
                                style={{ color: a.accuracy_pct >= 80 ? 'var(--teal)' : a.accuracy_pct >= 60 ? '#f59e0b' : '#ef4444' }}>
                            {a.accuracy_pct}%
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-[0.82rem] text-[var(--muted)]">{a.days_of_data} days</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
        </Card>
      )}

      {/* Inventory Health */}
      <Card>
        <CardHeader title="Inventory Health Overview" icon="📊"
          right={<Badge variant="teal">{s.total_products || 0} products</Badge>}
        />
        <CardBody>
          <div className="grid grid-cols-3 gap-6">
            {[
              { label:'Healthy Stock',   value: (s.total_products || 0) - (s.low_stock_count || 0), color:'#22c55e', icon:'✅' },
              { label:'Low / Out',       value: s.low_stock_count || 0,                              color:'#ef4444', icon:'⚠️' },
              { label:'AI Forecasted',   value: s.total_forecasted || 0,                             color:'#3b82f6', icon:'🤖' },
            ].map(h => (
              <div key={h.label} className="text-center py-6 border border-[var(--border)] rounded-[12px] bg-[var(--cream)]">
                <span className="text-2xl">{h.icon}</span>
                <p className="font-display font-bold text-[2rem] mt-2" style={{ color: h.color }}>{h.value}</p>
                <p className="text-[0.75rem] font-bold uppercase tracking-widest text-[var(--muted)] mt-1">{h.label}</p>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>
    </div>
  )
}
