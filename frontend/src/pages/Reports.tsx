import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getReports, createReport, retryReport } from "../api/queries"
import CountryPicker from "../components/CountryPicker"
import type { GeoCountry } from "../api/geo"

const STATUS_COLOR: Record<string, string> = {
  pending: "text-yellow-400 bg-yellow-900/30 border-yellow-700",
  generating: "text-blue-400 bg-blue-900/30 border-blue-700",
  ready: "text-emerald-400 bg-emerald-900/30 border-emerald-700",
  failed: "text-red-400 bg-red-900/30 border-red-700",
}

export default function Reports() {
  const [country, setCountry] = useState<GeoCountry | null>(null)
  const qc = useQueryClient()

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ["reports"],
    queryFn: getReports,
    refetchInterval: 8000,
  })

  const createMut = useMutation({
    mutationFn: () => createReport(country!.id, null, country!.properties.name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  })

  const retryMut = useMutation({
    mutationFn: (id: string) => retryReport(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  })

  return (
    <div className="min-h-screen bg-slate-900 px-6 py-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Reports</h1>
          <p className="text-slate-400 text-sm mt-1">Generate and download PDF market reports</p>
        </div>
        <div className="flex items-center gap-3">
          <CountryPicker value={country} onChange={setCountry} />
          <button
            onClick={() => createMut.mutate()}
            disabled={createMut.isPending || !country}
            className="bg-brand hover:bg-brand-light disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            {createMut.isPending ? "Generating..." : "Generate PDF"}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-slate-500">Loading...</div>
      ) : reports.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          No reports yet. Pick a country above and generate your first one.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {reports.map((r) => (
            <div
              key={r.id}
              className="bg-surface border border-slate-700 rounded-xl px-6 py-4 flex items-center justify-between"
            >
              <div>
                <p className="font-medium text-slate-200">{r.title}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {r.date_from} &rarr; {r.date_to}
                  {r.generated_at && " · " + new Date(r.generated_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-4">
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${STATUS_COLOR[r.status] ?? ""}`}>
                  {r.status}
                </span>
                {r.status === "ready" && r.file && (
                  <a
                    href={`/media/${r.file}`}
                    download
                    className="text-sm text-brand-light hover:text-white transition-colors font-semibold"
                  >
                    Download
                  </a>
                )}
                {(r.status === "pending" || r.status === "failed") && (
                  <button
                    onClick={() => retryMut.mutate(r.id)}
                    disabled={retryMut.isPending}
                    className="text-sm text-slate-400 hover:text-white transition-colors font-semibold disabled:opacity-50"
                  >
                    Retry
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
