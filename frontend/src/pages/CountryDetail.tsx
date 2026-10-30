import { useParams, useNavigate } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getTrend,
  getBusinessClimate,
  getSubscriptions,
  createSubscription,
  deleteSubscription,
} from "../api/queries"
import { getCountry } from "../api/geo"
import PriceChart from "../components/PriceChart"
import BusinessScorecard from "../components/BusinessScorecard"
import StatCard from "../components/StatCard"
import { useGeoViewStore } from "../store/geoView"
import { useAuthStore } from "../store/auth"

export default function CountryDetail() {
  const { iso2 = "", regionId } = useParams<{ iso2: string; regionId?: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const activeLayer = useGeoViewStore((s) => s.activeLayer)
  const token = useAuthStore((s) => s.accessToken)

  const { data: country } = useQuery({
    queryKey: ["country", iso2],
    queryFn: () => getCountry(iso2),
    enabled: !!iso2,
  })
  const region = country?.properties.regions.find((r) => r.id === regionId)
  const label = region ? region.name : country?.properties.name ?? iso2

  const { data: trend = [], isLoading: loadingTrend } = useQuery({
    queryKey: ["trend", iso2, regionId ?? null],
    queryFn: () => getTrend(iso2, regionId ?? null, 30),
    enabled: !!iso2 && activeLayer === "housing",
  })

  const { data: businessProfile, isLoading: loadingBusiness } = useQuery({
    queryKey: ["business-climate", iso2, regionId ?? null],
    queryFn: () => getBusinessClimate(iso2, regionId ?? null),
    enabled: !!iso2 && activeLayer === "business",
  })

  const { data: subs = [] } = useQuery({
    queryKey: ["subscriptions"],
    queryFn: getSubscriptions,
    enabled: !!token,
  })

  const activeSub = subs.find(
    (s) => s.country === country?.id && (s.region ?? null) === (regionId ?? null) && s.is_active,
  )

  const subscribeMut = useMutation({
    mutationFn: () => createSubscription(country!.id, regionId ?? null),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  })
  const unsubMut = useMutation({
    mutationFn: () => deleteSubscription(activeSub!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subscriptions"] }),
  })

  const latest = trend[trend.length - 1]
  const prev = trend[trend.length - 2]
  const change =
    latest && prev
      ? ((parseFloat(latest.avg_price_usd) - parseFloat(prev.avg_price_usd)) / parseFloat(prev.avg_price_usd)) * 100
      : null
  const minPrice = trend.length ? Math.min(...trend.map((d) => parseFloat(d.avg_price_usd))) : 0
  const maxPrice = trend.length ? Math.max(...trend.map((d) => parseFloat(d.avg_price_usd))) : 0

  return (
    <div className="min-h-screen bg-slate-900 px-6 py-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate("/")} className="text-slate-400 hover:text-white text-sm transition-colors">
            &larr; Back
          </button>
          <div>
            <h1 className="text-2xl font-bold">
              {country?.properties.flag_emoji} {label}
            </h1>
            <p className="text-slate-400 text-sm">
              {activeLayer === "housing" ? "Rental market — last 30 days" : "Business & investment climate"}
            </p>
          </div>
        </div>
        {activeLayer === "housing" && country && (
          token ? (
            <button
              onClick={() => (activeSub ? unsubMut.mutate() : subscribeMut.mutate())}
              disabled={subscribeMut.isPending || unsubMut.isPending}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                activeSub
                  ? "bg-slate-700 hover:bg-red-900/50 text-slate-300 hover:text-red-300"
                  : "bg-brand hover:bg-brand-light text-white"
              }`}
            >
              {activeSub ? "Unsubscribe" : "Subscribe to Alerts"}
            </button>
          ) : (
            <button
              onClick={() => navigate("/login")}
              className="px-4 py-2 rounded-lg text-sm font-semibold bg-slate-700 hover:bg-slate-600 text-slate-200 transition-all"
            >
              Sign in for Alerts
            </button>
          )
        )}
      </div>

      {activeLayer === "housing" ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard
              label="Avg Price"
              value={latest ? `$${parseFloat(latest.avg_price_usd).toFixed(0)}` : "—"}
              sub="per night"
              accent
              change={change}
              loading={loadingTrend}
            />
            <StatCard label="30d Min" value={minPrice ? `$${minPrice.toFixed(0)}` : "—"} sub="lowest in period" loading={loadingTrend} />
            <StatCard label="30d Max" value={maxPrice ? `$${maxPrice.toFixed(0)}` : "—"} sub="highest in period" loading={loadingTrend} />
            <StatCard label="Listings" value={latest?.listings_count ?? "—"} sub="latest snapshot" loading={loadingTrend} />
          </div>

          <div className="bg-surface border border-slate-700 rounded-2xl p-6">
            <h2 className="text-base font-semibold text-slate-200 mb-4">Price Trend</h2>
            {loadingTrend ? (
              <div className="h-[280px] flex items-center justify-center text-slate-500">Loading chart...</div>
            ) : trend.length === 0 ? (
              <div className="h-[280px] flex flex-col items-center justify-center text-center gap-3 px-6">
                <p className="text-slate-400 text-sm">
                  {label} isn't in our live housing-price tracking yet — we're expanding country
                  by country.
                </p>
                <p className="text-slate-500 text-xs">
                  {token
                    ? "Subscribe above and we'll notify you as soon as data lands."
                    : "Sign in to get notified as soon as data lands for this country."}
                </p>
              </div>
            ) : (
              <PriceChart data={trend} />
            )}
          </div>

          {country && country.properties.regions.length > 0 && !region && (
            <div className="mt-8">
              <h2 className="text-base font-semibold text-slate-200 mb-4">Regions</h2>
              <div className="flex flex-wrap gap-2">
                {country.properties.regions.map((r) => (
                  <button
                    key={r.id}
                    onClick={() => navigate(`/countries/${iso2}/regions/${r.id}`)}
                    className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-full transition-colors"
                  >
                    {r.name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </>
      ) : loadingBusiness ? (
        <div className="h-[280px] flex items-center justify-center text-slate-500">Loading...</div>
      ) : (
        <BusinessScorecard profile={businessProfile ?? null} />
      )}
    </div>
  )
}
