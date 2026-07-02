import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getSubscriptions, createSubscription, deleteSubscription } from "../api/queries"
import { getCountries, type GeoCountry } from "../api/geo"
import CountryPicker from "../components/CountryPicker"

export default function Subscriptions() {
  const qc = useQueryClient()
  const [country, setCountry] = useState<GeoCountry | null>(null)

  const { data: subs = [], isLoading } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: getSubscriptions,
  })
  const { data: countries = [] } = useQuery({ queryKey: ["countries"], queryFn: getCountries })
  const countryById: Record<string, GeoCountry> = {}
  for (const c of countries) countryById[c.id] = c

  const createMut = useMutation({
    mutationFn: () => createSubscription(country!.id, null),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["subscriptions"] })
      setCountry(null)
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteSubscription(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  })

  const activeSubs = subs.filter((s) => s.is_active)

  return (
    <div className="min-h-screen bg-slate-900 px-6 py-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Price Alerts</h1>
      <p className="text-slate-400 text-sm mb-6">
        Subscribe to a country to receive Telegram notifications when prices change by 5% or more.
      </p>

      <div className="flex items-center gap-3 mb-8">
        <CountryPicker value={country} onChange={setCountry} />
        <button
          onClick={() => createMut.mutate()}
          disabled={createMut.isPending || !country}
          className="bg-brand hover:bg-brand-light disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          Subscribe
        </button>
      </div>

      {isLoading ? (
        <div className="text-slate-500">Loading...</div>
      ) : activeSubs.length === 0 ? (
        <p className="text-center text-slate-500 mt-12">
          No active subscriptions. Search a country above to add one.
        </p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {activeSubs.map((sub) => {
            const c = countryById[sub.country]
            return (
              <div
                key={sub.id}
                className="bg-surface border border-brand-light/50 rounded-xl p-5 transition-all"
              >
                <div className="flex items-center justify-between mb-3">
                  <p className="font-semibold text-slate-200">
                    {c ? `${c.properties.flag_emoji} ${c.properties.name}` : sub.country}
                  </p>
                  <span className="text-xs text-emerald-400 bg-emerald-900/30 border border-emerald-700 px-2 py-0.5 rounded-full">
                    Active
                  </span>
                </div>
                <p className="text-xs text-slate-400 mb-3">
                  Alert when change &ge;{sub.threshold_pct}% ({sub.direction})
                </p>
                <button
                  onClick={() => deleteMut.mutate(sub.id)}
                  disabled={deleteMut.isPending}
                  className="w-full text-sm font-semibold py-2 rounded-lg transition-all bg-slate-700 hover:bg-red-900/40 text-slate-300 hover:text-red-300"
                >
                  Unsubscribe
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
