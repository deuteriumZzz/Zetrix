import { useRef, useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCountries, type GeoCountry } from '../api/geo'
import type { Aggregate } from '../api/queries'
import { useGeoViewStore } from '../store/geoView'

function priceColor(avg: number): string {
  if (avg < 100) return '#22c55e'
  if (avg < 150) return '#84cc16'
  if (avg < 200) return '#eab308'
  if (avg < 300) return '#f97316'
  return '#ef4444'
}

const NO_DATA_COLOR = '#475569'

interface Props {
  aggregates: Aggregate[]
  countries: GeoCountry[]
}

export default function GlobeMap({ aggregates, countries }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const activeLayer = useGeoViewStore((s) => s.activeLayer)
  const [GlobeGL, setGlobeGL] = useState<any>(null)
  const [size, setSize] = useState({ w: 500, h: 500 })
  const [selected, setSelected] = useState<GeoCountry | null>(null)
  const globeRef = useRef<any>(null)

  useEffect(() => {
    import('react-globe.gl').then((m) => setGlobeGL(() => m.default))
  }, [])

  useEffect(() => {
    if (!containerRef.current) return
    const obs = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      setSize({ w: Math.round(width), h: Math.round(height) })
    })
    obs.observe(containerRef.current)
    return () => obs.disconnect()
  }, [])

  const priceByCountry = useMemo(() => {
    const map: Record<string, number> = {}
    for (const agg of aggregates) {
      if (agg.market_type === 'rental' && !agg.region && !map[agg.country]) {
        map[agg.country] = parseFloat(agg.avg_price_usd)
      }
    }
    return map
  }, [aggregates])

  const worldPoints = useMemo(
    () =>
      countries.map((c) => {
        const avg = priceByCountry[c.id] ?? 0
        const color =
          activeLayer === 'housing'
            ? avg > 0
              ? priceColor(avg)
              : NO_DATA_COLOR
            : NO_DATA_COLOR // business-climate bulk data not yet available on the world view
        return {
          iso2: c.properties.iso2,
          lat: c.properties.centroid_lat,
          lng: c.properties.centroid_lng,
          country: c,
          color,
          size: avg > 0 ? 0.35 + avg / 900 : 0.22,
          htmlLabel: `<div style="background:#1e293b;border:1px solid #334155;padding:8px 12px;border-radius:8px;font-size:13px;white-space:nowrap;color:#fff;pointer-events:none">
            <b>${c.properties.flag_emoji} ${c.properties.name}</b><br/>
            ${
              avg > 0
                ? `<span style="color:#94a3b8">avg</span> <b style="color:#3B82C4">$${avg.toFixed(0)}</b>/night`
                : '<span style="color:#64748b">no data yet</span>'
            }
          </div>`,
        }
      }),
    [countries, priceByCountry, activeLayer],
  )

  const regionPoints = useMemo(() => {
    if (!selected) return []
    return selected.properties.regions.map((r) => ({
      slug: r.slug,
      id: r.id,
      lat: r.centroid_lat,
      lng: r.centroid_lng,
      color: '#3B82C4',
      size: 0.3,
      htmlLabel: `<div style="background:#1e293b;border:1px solid #334155;padding:6px 10px;border-radius:8px;font-size:12px;white-space:nowrap;color:#fff;pointer-events:none"><b>${r.name}</b></div>`,
    }))
  }, [selected])

  const handleWorldPointClick = (d: any) => {
    const country: GeoCountry = d.country
    if (country.properties.regions.length > 0) {
      setSelected(country)
      globeRef.current?.pointOfView(
        { lat: country.properties.centroid_lat, lng: country.properties.centroid_lng, altitude: 0.5 },
        1000,
      )
    } else {
      navigate(`/countries/${country.properties.iso2}`)
    }
  }

  const handleRegionPointClick = (d: any) => {
    if (!selected) return
    navigate(`/countries/${selected.properties.iso2}/regions/${d.id}`)
  }

  return (
    <div ref={containerRef} className="w-full h-full relative">
      {selected && (
        <button
          onClick={() => {
            setSelected(null)
            globeRef.current?.pointOfView({ lat: 10, lng: 0, altitude: 2.2 }, 1000)
          }}
          className="absolute top-3 left-3 z-10 text-xs bg-slate-800/90 hover:bg-slate-700 text-slate-200 px-3 py-1.5 rounded-full border border-slate-600"
        >
          &larr; World
        </button>
      )}
      {GlobeGL ? (
        <GlobeGL
          ref={globeRef}
          globeImageUrl="//unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
          backgroundImageUrl="//unpkg.com/three-globe/example/img/night-sky.png"
          pointsData={selected ? regionPoints : worldPoints}
          pointAltitude="size"
          pointColor="color"
          pointRadius={0.35}
          pointLabel="htmlLabel"
          onPointClick={selected ? handleRegionPointClick : handleWorldPointClick}
          pointOfView={{ lat: 10, lng: 0, altitude: 2.2 }}
          animateIn={false}
          width={size.w}
          height={size.h}
        />
      ) : (
        <div className="flex items-center justify-center h-full text-slate-500">
          Loading globe...
        </div>
      )}
    </div>
  )
}
