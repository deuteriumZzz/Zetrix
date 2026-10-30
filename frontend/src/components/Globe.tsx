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

const NO_DATA_COLOR = '#40515b'

const HTML_ENTITIES: Record<string, string> = {
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => HTML_ENTITIES[character])
}

interface Props {
  aggregates: Aggregate[]
  countries: GeoCountry[]
}

export default function GlobeMap({ aggregates, countries }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const activeLayer = useGeoViewStore((s) => s.activeLayer)
  const [GlobeGL, setGlobeGL] = useState<any>(null)
  const [loadFailed, setLoadFailed] = useState(false)
  const [size, setSize] = useState({ w: 500, h: 500 })
  const [selected, setSelected] = useState<GeoCountry | null>(null)
  const globeRef = useRef<any>(null)

  useEffect(() => {
    import('react-globe.gl')
      .then((m) => setGlobeGL(() => m.default))
      .catch(() => setLoadFailed(true))
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

  useEffect(() => {
    const controls = globeRef.current?.controls()
    if (controls) {
      controls.autoRotate = !selected && !window.matchMedia('(prefers-reduced-motion: reduce)').matches
    }
  }, [selected, GlobeGL])

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
        const hasRegions = c.properties.regions.length > 0
        const color = activeLayer === 'housing'
          ? avg > 0 ? priceColor(avg) : NO_DATA_COLOR
          : hasRegions ? '#d66c60' : c.properties.is_housing_supported ? '#74bbc5' : NO_DATA_COLOR
        return {
          iso2: c.properties.iso2,
          lat: c.properties.centroid_lat,
          lng: c.properties.centroid_lng,
          country: c,
          color,
          size: activeLayer === 'housing'
            ? avg > 0 ? 0.35 + avg / 900 : 0.16
            : hasRegions ? 0.42 : c.properties.is_housing_supported ? 0.3 : 0.14,
          htmlLabel: `<div style="background:#1e293b;border:1px solid #334155;padding:8px 12px;border-radius:8px;font-size:13px;white-space:nowrap;color:#fff;pointer-events:none">
            <b>${c.properties.flag_emoji} ${escapeHtml(c.properties.name)}</b><br/>
            ${activeLayer === 'housing'
              ? avg > 0
                ? `<span style="color:#94a3b8">avg</span> <b style="color:#74bbc5">$${avg.toFixed(0)}</b>/night`
                : '<span style="color:#a4aaac">housing data unavailable</span>'
              : c.properties.regions.length > 0
                ? `<span style="color:#aeb8ba">${c.properties.regions.length} regional entries</span>`
                : c.properties.is_housing_supported
                  ? '<span style="color:#aeb8ba">regional coverage in progress</span>'
                  : '<span style="color:#aeb8ba">select to explore available data</span>'}
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
      color: '#d66c60',
      size: 0.38,
      htmlLabel: `<div style="background:#1e293b;border:1px solid #334155;padding:6px 10px;border-radius:8px;font-size:12px;white-space:nowrap;color:#fff;pointer-events:none"><b>${escapeHtml(r.name)}</b></div>`,
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
      {loadFailed ? (
        <div className="flex items-center justify-center h-full text-slate-500 text-sm text-center px-6">
          Couldn't load the 3D globe. Try refreshing, or use the search box to jump to a country.
        </div>
      ) : GlobeGL ? (
        <GlobeGL
          ref={globeRef}
          globeImageUrl="/globe/earth-blue-marble.jpg"
          backgroundImageUrl="/globe/night-sky.png"
          backgroundColor="rgba(0,0,0,0)"
          showAtmosphere
          atmosphereColor="#5c9ca7"
          atmosphereAltitude={0.18}
          showGraticules
          pointsData={selected ? regionPoints : worldPoints}
          pointAltitude="size"
          pointColor="color"
          pointRadius={0.38}
          pointResolution={10}
          pointsTransitionDuration={900}
          pointLabel="htmlLabel"
          onPointClick={selected ? handleRegionPointClick : handleWorldPointClick}
          pointOfView={{ lat: 10, lng: 0, altitude: 2.2 }}
          animateIn={false}
          width={size.w}
          height={size.h}
          onGlobeReady={() => {
            const controls = globeRef.current?.controls()
            if (controls) {
              controls.autoRotate = !selected && !window.matchMedia('(prefers-reduced-motion: reduce)').matches
              controls.autoRotateSpeed = 0.42
              controls.enableDamping = true
              controls.dampingFactor = 0.08
              controls.enableZoom = true
            }
          }}
        />
      ) : (
        <div className="flex items-center justify-center h-full text-slate-500">
          Loading globe...
        </div>
      )}
    </div>
  )
}
