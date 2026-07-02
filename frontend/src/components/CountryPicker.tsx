import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { getCountries, type GeoCountry } from "../api/geo"

interface Props {
  value: GeoCountry | null
  onChange: (country: GeoCountry) => void
}

export default function CountryPicker({ value, onChange }: Props) {
  const [query, setQuery] = useState("")
  const [open, setOpen] = useState(false)
  const { data: countries = [] } = useQuery({ queryKey: ["countries"], queryFn: getCountries })

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return countries.slice(0, 8)
    return countries.filter((c) => c.properties.name.toLowerCase().includes(q)).slice(0, 8)
  }, [query, countries])

  return (
    <div className="relative">
      <input
        value={open ? query : value ? `${value.properties.flag_emoji} ${value.properties.name}` : query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Search a country..."
        className="bg-slate-800 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-light w-56"
      />
      {open && filtered.length > 0 && (
        <div className="absolute z-10 mt-1 w-56 bg-slate-800 border border-slate-600 rounded-lg overflow-hidden max-h-64 overflow-y-auto">
          {filtered.map((c) => (
            <button
              key={c.properties.iso2}
              onMouseDown={() => {
                onChange(c)
                setQuery("")
                setOpen(false)
              }}
              className="w-full text-left px-3 py-2 text-sm text-slate-300 hover:bg-slate-700"
            >
              {c.properties.flag_emoji} {c.properties.name}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
