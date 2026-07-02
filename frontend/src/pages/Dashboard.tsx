import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { getAggregates } from "../api/queries"
import { getCountries } from "../api/geo"
import GlobeMap from "../components/Globe"
import StatCard from "../components/StatCard"
import { useGeoViewStore } from "../store/geoView"

export default function Dashboard() {
  const navigate = useNavigate()
  const [search, setSearch] = useState("")
  const activeLayer = useGeoViewStore((s) => s.activeLayer)
  const setLayer = useGeoViewStore((s) => s.setLayer)

  const { data: aggregates = [], isLoading: loadingAgg } = useQuery({
    queryKey: ["aggregates"],
    queryFn: getAggregates,
  })
  const { data: countries = [], isLoading: loadingCountries } = useQuery({
    queryKey: ["countries"],
    queryFn: getCountries,
  })
  const isLoading = loadingAgg || loadingCountries

  const priceByCountry: Record<string, number> = {}
  for (const agg of aggregates) {
    if (agg.market_type === "rental" && !agg.region && !priceByCountry[agg.country]) {
      priceByCountry[agg.country] = parseFloat(agg.avg_price_usd)
    }
  }

  const supportedCountries = countries.filter((c) => c.properties.is_housing_supported)
  const withData = supportedCountries.filter((c) => priceByCountry[c.id] != null)
  const totalListings = aggregates
    .filter((a) => a.market_type === "rental" && !a.region)
    .reduce((s, a) => s + a.listings_count, 0)
  const changes = aggregates
    .filter((a) => a.market_type === "rental" && !a.region && a.price_change_pct != null)
    .map((a) => parseFloat(a.price_change_pct!))
  const avgChange = changes.length ? changes.reduce((s, c) => s + c, 0) / changes.length : 0

  const filtered = useMemo(() => {
    if (!search.trim()) return []
    const q = search.trim().toLowerCase()
    return countries.filter((c) => c.properties.name.toLowerCase().includes(q)).slice(0, 8)
  }, [search, countries])

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Hero */}
      <div className="flex flex-col lg:flex-row gap-0 lg:h-[560px]">
        {/* Globe */}
        <div className="lg:flex-1 h-[360px] lg:h-full bg-slate-950 relative overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-slate-500">
              Loading...
            </div>
          ) : (
            <GlobeMap aggregates={aggregates} countries={countries} />
          )}
          <div className="absolute bottom-4 left-4 text-xs text-slate-500">
            Click a country to explore
          </div>
          <div className="absolute top-3 right-3 z-10 flex bg-slate-800/90 border border-slate-600 rounded-full p-1 text-xs">
            <button
              onClick={() => setLayer("housing")}
              className={`px-3 py-1 rounded-full transition-colors ${
                activeLayer === "housing" ? "bg-brand text-white" : "text-slate-300"
              }`}
            >
              Housing
            </button>
            <button
              onClick={() => setLayer("business")}
              className={`px-3 py-1 rounded-full transition-colors ${
                activeLayer === "business" ? "bg-brand text-white" : "text-slate-300"
              }`}
            >
              Business
            </button>
          </div>
        </div>

        {/* Stats sidebar */}
        <div className="lg:w-80 p-6 flex flex-col gap-4 border-l border-slate-800">
          <h1 className="text-lg font-bold text-slate-200">Market Overview</h1>
          <StatCard label="Countries Tracked" value={withData.length} sub={`of ${countries.length} worldwide`} accent />
          <StatCard label="Total Listings" value={totalListings.toLocaleString()} sub="across all countries" />
          <StatCard
            label="Avg Price Change"
            value={`${avgChange > 0 ? "+" : ""}${avgChange.toFixed(1)}%`}
            sub="vs yesterday"
            change={avgChange}
          />
          <div className="mt-auto pt-4 border-t border-slate-700">
            <p className="text-xs text-slate-500 mb-2">Search a country</p>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="e.g. Indonesia"
              className="w-full bg-slate-800 border border-slate-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-brand-light"
            />
            {filtered.length > 0 && (
              <div className="mt-2 flex flex-col gap-1">
                {filtered.map((c) => (
                  <button
                    key={c.properties.iso2}
                    onClick={() => navigate(`/countries/${c.properties.iso2}`)}
                    className="text-left text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    {c.properties.flag_emoji} {c.properties.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Country cards grid — countries with live housing data */}
      <div className="px-6 py-8">
        <h2 className="text-lg font-semibold text-slate-200 mb-4">Tracked Countries — Rental</h2>
        {isLoading ? (
          <div className="text-slate-500">Loading...</div>
        ) : supportedCountries.length === 0 ? (
          <div className="text-slate-500">No countries have housing data yet.</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {supportedCountries.map((c) => {
              const avg = priceByCountry[c.id]
              const agg = aggregates.find(
                (a) => a.country === c.id && a.market_type === "rental" && !a.region,
              )
              return (
                <button
                  key={c.properties.iso2}
                  onClick={() => navigate(`/countries/${c.properties.iso2}`)}
                  className="bg-surface border border-slate-700 hover:border-brand-light rounded-xl p-4 text-left transition-all group"
                >
                  <p className="text-xs text-slate-400 mb-2">
                    {c.properties.flag_emoji} {c.properties.name}
                  </p>
                  {avg != null ? (
                    <>
                      <p className="text-xl font-bold text-white">${avg.toFixed(0)}</p>
                      <p className="text-xs text-slate-400">/night avg</p>
                      {agg?.price_change_pct && (
                        <p
                          className={`text-xs font-semibold mt-1 ${
                            parseFloat(agg.price_change_pct) > 0 ? "text-emerald-400" : "text-red-400"
                          }`}
                        >
                          {parseFloat(agg.price_change_pct) > 0 ? "+" : ""}
                          {parseFloat(agg.price_change_pct).toFixed(1)}%
                        </p>
                      )}
                      {agg && <p className="text-xs text-slate-500 mt-1">{agg.listings_count} listings</p>}
                    </>
                  ) : (
                    <p className="text-xs text-slate-600">No data</p>
                  )}
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
