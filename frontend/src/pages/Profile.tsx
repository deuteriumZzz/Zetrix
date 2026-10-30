import { useEffect, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getProfile, updateProfile } from "../api/queries"
import { getCountries, type GeoCountry } from "../api/geo"
import CountryPicker from "../components/CountryPicker"

export default function Profile() {
  const qc = useQueryClient()
  const { data: profile, isLoading } = useQuery({ queryKey: ["profile"], queryFn: getProfile })
  const { data: countries = [] } = useQuery({ queryKey: ["countries"], queryFn: getCountries })

  const [telegramChatId, setTelegramChatId] = useState("")
  const [preferredCountry, setPreferredCountry] = useState<GeoCountry | null>(null)
  const [marketType, setMarketType] = useState("rental")

  useEffect(() => {
    if (!profile) return
    setTelegramChatId(profile.telegram_chat_id ?? "")
    setMarketType(profile.preferred_market_type)
  }, [profile])

  useEffect(() => {
    if (!profile?.preferred_country || countries.length === 0) return
    const match = countries.find((c) => c.id === profile.preferred_country)
    if (match) setPreferredCountry(match)
  }, [profile, countries])

  const mutation = useMutation({
    mutationFn: () =>
      updateProfile({
        telegram_chat_id: telegramChatId || null,
        preferred_country: preferredCountry?.id ?? null,
        preferred_market_type: marketType,
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  })

  if (isLoading) {
    return <div className="min-h-screen bg-slate-900 px-6 py-8 text-slate-500">Loading...</div>
  }

  return (
    <div className="min-h-screen bg-slate-900 px-6 py-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">Profile</h1>
      <p className="text-slate-400 text-sm mb-8">{profile?.username} &middot; {profile?.email || "no email set"}</p>

      <form
        onSubmit={(e) => { e.preventDefault(); mutation.mutate() }}
        className="bg-surface border border-slate-700 rounded-2xl p-6 flex flex-col gap-6"
      >
        <div>
          <label className="text-xs text-slate-400 uppercase tracking-widest block mb-2">
            Telegram Chat ID
          </label>
          <p className="text-xs text-slate-500 mb-2">
            Message our bot and send <code className="text-slate-400">/start</code> — it will
            reply with your Chat ID. Paste it here to receive alerts and reports on Telegram.
          </p>
          <input
            value={telegramChatId}
            onChange={(e) => setTelegramChatId(e.target.value)}
            placeholder="e.g. 123456789"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-brand-light"
          />
        </div>

        <div>
          <label className="text-xs text-slate-400 uppercase tracking-widest block mb-2">
            Preferred country
          </label>
          <CountryPicker value={preferredCountry} onChange={setPreferredCountry} />
        </div>

        <div>
          <label className="text-xs text-slate-400 uppercase tracking-widest block mb-2">
            Preferred market
          </label>
          <select
            value={marketType}
            onChange={(e) => setMarketType(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-brand-light"
          >
            <option value="rental">Rental</option>
            <option value="real_estate">Real Estate</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="bg-brand hover:bg-brand-light disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors"
        >
          {mutation.isPending ? "Saving..." : "Save changes"}
        </button>
        {mutation.isSuccess && <p className="text-sm text-emerald-400 text-center">Saved.</p>}
      </form>
    </div>
  )
}
