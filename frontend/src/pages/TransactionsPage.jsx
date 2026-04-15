import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { posService } from '../services/apiServices'
import { Card, CardHeader } from '../components/ui/Card'
import Badge  from '../components/ui/Badge'
import LoadingSpinner from '../components/ui/LoadingSpinner'

export default function TransactionsPage() {
  const [page, setPage] = useState(1)
  const { data, loading } = useApi(() => posService.getSales({ page, per_page: 20 }), null, [page])

  const sales = data?.data  || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / 20)

  // Stats
  const totalRevenue = sales.reduce((s, sale) => s + (sale.total || 0), 0)
  const totalItems   = sales.reduce((s, sale) => s + (sale.items?.length || 0), 0)

  return (
    <div className="space-y-5">

      {/* Header */}
      <div>
        <h2 className="font-display font-bold text-[1.3rem] text-[var(--ink)]">Transaction History</h2>
        <p className="text-[0.82rem] text-[var(--muted)] mt-0.5">
          View all your completed sales and billing records
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label:'Total Transactions', value: total,           icon:'🧾', color:'var(--teal)' },
          { label:'Page Revenue',       value: `₹${totalRevenue.toLocaleString('en-IN')}`, icon:'💰', color:'#22c55e' },
          { label:'Items Sold',         value: totalItems,      icon:'📦', color:'#3b82f6' },
        ].map(s => (
          <div key={s.label} className="bg-white border border-[var(--border)] rounded-[12px] px-5 py-4"
               style={{ boxShadow:'var(--shadow-sm)' }}>
            <div className="flex items-center justify-between mb-1">
              <p className="text-[0.7rem] font-extrabold uppercase tracking-widest text-[var(--muted)]">{s.label}</p>
              <span className="text-lg">{s.icon}</span>
            </div>
            <p className="font-display font-bold text-[1.6rem] leading-none" style={{ color:s.color }}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Transactions Table */}
      <Card>
        <CardHeader title={`All Transactions (${total})`} icon="🧾"
          right={
            <div className="flex items-center gap-2">
              <Badge variant="teal">Page {page} of {Math.max(totalPages, 1)}</Badge>
            </div>
          }
        />
        {loading ? <LoadingSpinner /> : (
          sales.length === 0 ? (
            <div className="px-5 py-12 text-center">
              <span className="text-4xl block mb-3">🧾</span>
              <p className="font-semibold text-[var(--ink)] text-[0.95rem] mb-1">No transactions yet</p>
              <p className="text-[0.82rem] text-[var(--muted)]">
                Sales recorded via POS billing will appear here.
              </p>
            </div>
          ) : (
            <>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    {['Date & Time','Items','Subtotal','Tax (GST)','Total','Payment'].map(h => (
                      <th key={h} className="px-5 py-3 text-left text-[0.67rem] font-extrabold tracking-widest
                                             uppercase text-[var(--muted)] border-b border-[var(--border)] bg-[var(--cream)]">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sales.map(sale => {
                    const itemNames = sale.items?.map(i => i.name).filter(Boolean).join(', ') || '—'
                    const itemCount = sale.items?.length || 0

                    return (
                      <tr key={sale.id}
                          className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--teal-pale)] transition-colors">
                        <td className="px-5 py-3">
                          <p className="font-semibold text-[0.85rem] text-[var(--ink)]">
                            {new Date(sale.created_at).toLocaleDateString('en-IN', {
                              day:'2-digit', month:'short', year:'numeric'
                            })}
                          </p>
                          <p className="text-[0.72rem] text-[var(--muted)]">
                            {new Date(sale.created_at).toLocaleTimeString('en-IN', {
                              hour:'2-digit', minute:'2-digit'
                            })}
                          </p>
                        </td>
                        <td className="px-5 py-3">
                          <p className="font-semibold text-[0.85rem] text-[var(--ink)]">{itemCount} items</p>
                          <p className="text-[0.72rem] text-[var(--muted)] max-w-[200px] truncate">{itemNames}</p>
                        </td>
                        <td className="px-5 py-3 text-[0.85rem] text-[var(--ink)]">
                          ₹{(sale.subtotal || 0).toLocaleString('en-IN')}
                        </td>
                        <td className="px-5 py-3 text-[0.82rem] text-[var(--muted)]">
                          ₹{(sale.tax || 0).toLocaleString('en-IN')}
                        </td>
                        <td className="px-5 py-3 font-bold text-[0.9rem] text-[var(--teal)]">
                          ₹{(sale.total || 0).toLocaleString('en-IN')}
                        </td>
                        <td className="px-5 py-3">
                          <Badge variant="teal">✓ Paid</Badge>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-5 py-3 border-t border-[var(--border)] bg-[var(--cream)]">
                  <p className="text-[0.78rem] text-[var(--muted)]">
                    Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, total)} of {total}
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page <= 1}
                      className="text-[0.78rem] font-semibold px-3 py-1.5 rounded-[8px] border border-[var(--border)]
                                 bg-white hover:bg-[var(--teal-pale)] disabled:opacity-40 disabled:cursor-not-allowed
                                 cursor-pointer transition-colors text-[var(--ink)]">
                      ← Prev
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                      className="text-[0.78rem] font-semibold px-3 py-1.5 rounded-[8px] border border-[var(--border)]
                                 bg-white hover:bg-[var(--teal-pale)] disabled:opacity-40 disabled:cursor-not-allowed
                                 cursor-pointer transition-colors text-[var(--ink)]">
                      Next →
                    </button>
                  </div>
                </div>
              )}
            </>
          )
        )}
      </Card>
    </div>
  )
}
