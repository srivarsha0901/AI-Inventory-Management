import { useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi'
import { alertService } from '../services/apiServices'
import { Card, CardHeader } from '../components/ui/Card'
import { useMLStatus } from '../hooks/useMLStatus'
import WaitingForData from '../components/ui/WaitingForData'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import LoadingSpinner from '../components/ui/LoadingSpinner'

const TYPE_STYLES = {
  critical: { variant:'red',   bg:'#fee2e2', label:'Critical' },
  warning:  { variant:'amber', bg:'#fef3c7', label:'Warning'  },
  info:     { variant:'blue',  bg:'#eff6ff', label:'Info'     },
  success:  { variant:'teal',  bg:'#ecfdf5', label:'Resolved' },
}

export function AlertsPage() {
  const navigate = useNavigate()
  const { hasMLPredictions, hasInventory } = useMLStatus()
  const { data, loading, refetch } = useApi(alertService.getAll)

  const alerts = data?.data?.map((a) => ({
    id:   a.id,
    type: a.severity === 'critical' ? 'critical'
        : a.severity === 'warning'  ? 'warning'
        : a.severity === 'info'     ? 'info'
        : 'success',
    icon: a.type === 'expiry'    ? '⏰'
        : a.type === 'low_stock' ? '📦'
        : '🔔',
    name: a.product_name + ' — ' + (a.message.split('—')[0]?.trim() || a.message),
    meta: a.message,
    time: new Date(a.created_at).toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' }),
  })) || []

  // Early returns AFTER all hooks
  if (!hasInventory) return (
    <WaitingForData
      icon="📦"
      title="Add your inventory first"
      message="Add your store's products before alerts can be generated."
      actionLabel="Add Inventory →"
      actionTo="/onboarding"
    />
  )

  if (!hasMLPredictions) return (
    <WaitingForData
      icon="🔔"
      title="No alerts yet"
      message="Alerts will appear once AI has analysed your sales patterns. Upload your past sales history to activate smart alerts immediately."
      actionLabel="Upload Sales History →"
      actionTo="/onboarding"
      secondaryLabel="I'll record sales via POS instead"
      onSecondary={() => navigate('/pos')}
    />
  )

  return (
    <div className="space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display font-bold text-[1.3rem] text-[var(--ink)]">Alerts Center</h2>
          <p className="text-[0.82rem] text-[var(--muted)] mt-0.5">
            All low-stock, expiry, and reorder alerts in one place
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={refetch}>↻ Refresh</Button>
          <Button variant="danger"  size="sm">Dismiss All</Button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label:'Critical', value: alerts.filter(a=>a.type==='critical').length, color:'#ef4444' },
          { label:'Warnings', value: alerts.filter(a=>a.type==='warning').length,  color:'#f59e0b' },
          { label:'Info',     value: alerts.filter(a=>a.type==='info').length,     color:'#3b82f6' },
          { label:'Resolved', value: alerts.filter(a=>a.type==='success').length,  color:'#22c55e' },
        ].map((s) => (
          <div key={s.label}
               className="bg-white border border-[var(--border)] rounded-[12px] px-5 py-4"
               style={{ boxShadow:'var(--shadow-sm)' }}>
            <p className="text-[0.7rem] font-extrabold uppercase tracking-widest text-[var(--muted)] mb-1">
              {s.label}
            </p>
            <p className="font-display font-bold text-[1.8rem]" style={{ color: s.color }}>
              {s.value}
            </p>
          </div>
        ))}
      </div>

      {/* Alerts list */}
      <Card>
        <CardHeader
          title={`All Alerts (${alerts.length})`}
          icon="⚡"
          right={<Badge variant="red">Live</Badge>}
        />
        {loading ? <LoadingSpinner /> : (
          alerts.length === 0 ? (
            <div className="px-5 py-10 text-center text-[var(--muted)] text-sm">
              ✅ No active alerts. Everything looks good!
            </div>
          ) : (
            <div>
              {alerts.map((a) => {
                const t = TYPE_STYLES[a.type] || TYPE_STYLES.info
                return (
                  <div key={a.id}
                       className="flex items-start gap-3 px-5 py-4 border-b border-[var(--border)]
                                  last:border-0 hover:bg-[var(--cream)] transition-colors">
                    <div className="w-9 h-9 rounded-[9px] flex items-center justify-center text-base flex-shrink-0"
                         style={{ background: t.bg }}>
                      {a.icon}
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-[0.85rem] text-[var(--ink)]">{a.name}</p>
                      <p className="text-[0.74rem] text-[var(--muted)] mt-0.5">{a.meta}</p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-[0.72rem] text-[var(--muted)]">{a.time}</span>
                      <Badge variant={t.variant}>{t.label}</Badge>
                      <button
                        className="text-[0.74rem] text-[var(--muted)] hover:text-red-500
                                   font-medium bg-transparent border-0 cursor-pointer"
                        onClick={async () => {
                          await alertService.dismiss(a.id)
                          refetch()
                        }}>
                        Dismiss
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        )}
      </Card>
    </div>
  )
}