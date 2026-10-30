interface Props {
  label: string
  value: string | number
  sub?: string
  accent?: boolean
  change?: number | null
  loading?: boolean
}

export default function StatCard({ label, value, sub, accent, change, loading }: Props) {
  const changeColor = change == null ? "" : change > 0 ? "text-emerald-400" : "text-red-400"
  const changeSign = change != null && change > 0 ? "+" : ""

  if (loading) {
    return (
      <div className={`rounded-xl p-5 border animate-pulse ${accent ? "bg-brand border-brand-light/30" : "bg-surface border-slate-700"}`}>
        <div className="h-3 w-20 bg-white/10 rounded mb-3" />
        <div className="h-6 w-16 bg-white/10 rounded mb-2" />
        <div className="h-3 w-24 bg-white/10 rounded" />
      </div>
    )
  }

  return (
    <div className={`rounded-xl p-5 border ${accent ? "bg-brand border-brand-light/30" : "bg-surface border-slate-700"}`}>
      <p className="text-xs text-slate-400 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
      {change != null && (
        <p className={`text-sm font-semibold mt-1 ${changeColor}`}>
          {changeSign}{change.toFixed(1)}% vs yesterday
        </p>
      )}
    </div>
  )
}
