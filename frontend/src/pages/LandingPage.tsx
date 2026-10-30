import { useEffect, useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { getAggregates } from "../api/queries"
import { getCountries } from "../api/geo"
import GlobeMap from "../components/Globe"
import { useGeoViewStore } from "../store/geoView"

export default function LandingPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState("")
  const activeLayer = useGeoViewStore((state) => state.activeLayer)
  const setLayer = useGeoViewStore((state) => state.setLayer)
  const { data: aggregates = [], isLoading: loadingAggregates } = useQuery({
    queryKey: ["aggregates"],
    queryFn: getAggregates,
  })
  const { data: countries = [], isLoading: loadingCountries } = useQuery({
    queryKey: ["countries"],
    queryFn: getCountries,
  })
  const loading = loadingAggregates || loadingCountries
  const regionalCountries = countries.filter((country) => country.properties.regions.length > 0)
  const regionCount = countries.reduce((total, country) => total + country.properties.regions.length, 0)
  const supportedHousing = countries.filter((country) => country.properties.is_housing_supported).length
  const listings = aggregates
    .filter((aggregate) => aggregate.market_type === "rental" && !aggregate.region)
    .reduce((total, aggregate) => total + aggregate.listings_count, 0)

  useEffect(() => {
    const sections = document.querySelectorAll<HTMLElement>(".zh-reveal")
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      sections.forEach((section) => section.classList.add("is-visible"))
      return
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible")
          observer.unobserve(entry.target)
        }
      })
    }, { threshold: 0.12, rootMargin: "0px 0px -7% 0px" })
    sections.forEach((section) => observer.observe(section))
    return () => observer.disconnect()
  }, [])

  const results = useMemo(() => {
    if (!search.trim()) return []
    const query = search.trim().toLocaleLowerCase()
    return countries.filter((country) => country.properties.name.toLocaleLowerCase().includes(query)).slice(0, 5)
  }, [countries, search])

  return (
    <main className="zetrix-site">
      <section className="zh-hero" aria-labelledby="hero-title">
        <div className="zh-hero-copy">
          <p className="zh-kicker"><span className="zh-live-dot" />GLOBAL BUSINESS INTELLIGENCE</p>
          <h1 id="hero-title">Make the<br />world your<br /><em>next move.</em></h1>
          <p className="zh-hero-lede">
            Understand what doing business really looks like—country by country, region by region.
            Zetrix brings the world into focus before you decide where to go next.
          </p>
          <div className="zh-hero-actions">
            <a className="zh-button" href="#planet">Explore the globe <span aria-hidden="true">↗</span></a>
            <a className="zh-text-link" href="#technology">Discover Zetrix <span aria-hidden="true">↓</span></a>
          </div>
          <div className="zh-hero-search">
            <label htmlFor="country-search">FIND A COUNTRY</label>
            <input id="country-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by country name" autoComplete="off" />
            {results.length > 0 && <div className="zh-search-results">
              {results.map((country) => <button key={country.properties.iso2} type="button" onClick={() => navigate(`/countries/${country.properties.iso2}`)}>
                <span>{country.properties.flag_emoji} {country.properties.name}</span><span aria-hidden="true">↗</span>
              </button>)}
            </div>}
          </div>
          <p className="zh-hero-caption">A clearer view of business regions around the planet.</p>
        </div>

        <div className="zh-hero-visual" id="planet" aria-label="Interactive 3D globe">
          <div className="zh-visual-topline"><span>PLANETARY VIEW</span><span>01 — WORLD</span></div>
          <div className="zh-hero-globe">
            <div className="zh-globe-halo" />
            <div className="zh-globe-stage">
              <GlobeMap aggregates={aggregates} countries={countries} />
              {loading && <span className="zh-globe-loading">SYNCING GLOBAL DATA</span>}
            </div>
            <div className="zh-floating-label label-north"><span className="zh-label-dot" />COUNTRY CONTEXT</div>
            <div className="zh-floating-label label-south"><span className="zh-label-dot" />REGIONAL DETAIL</div>
          </div>
          <div className="zh-visual-controls">
            <div className="zh-map-layers" role="group" aria-label="Map layer">
              <button type="button" className={activeLayer === "business" ? "selected" : ""} onClick={() => setLayer("business")}>Business</button>
              <button type="button" className={activeLayer === "housing" ? "selected" : ""} onClick={() => setLayer("housing")}>Housing</button>
            </div>
            <span>DRAG TO ORIENT <b>↗</b></span>
          </div>
          <div className="zh-visual-bottomline"><span>Rotate · Select · Explore</span><span>WORLD / 001</span></div>
        </div>
      </section>

      <section className="zh-vision zh-reveal" id="about">
        <div className="zh-section-label">01 / THE VISION</div>
        <div className="zh-vision-main">
          <h2>Business doesn’t happen on a map.<br /><em>It happens in a place.</em></h2>
          <div className="zh-vision-copy">
            <p>Every market has its own rules, costs, opportunities, and friction. The country is only the first layer.</p>
            <p>Zetrix brings regional business conditions and market signals into one geographic view—so you can see more of the place behind the numbers.</p>
          </div>
        </div>
        <div className="zh-vision-quote"><span className="zh-quote-mark">“</span><p>From a global question<br />to a region you can understand.</p><span className="zh-quote-index">ZETRIX / 2026</span></div>
      </section>

      <section className="zh-product zh-reveal" id="technology">
        <div className="zh-product-intro">
          <div>
            <p className="zh-kicker zh-kicker-light">02 / THE PLATFORM</p>
            <h2>One planet.<br /><em>Different realities.</em></h2>
          </div>
          <p>Move from country to region. Explore business climate alongside the signals that shape local markets. The globe is your starting point; each place opens a more specific view.</p>
        </div>
        <div className="zh-platform-grid">
          <article className="zh-platform-card zh-platform-card-featured">
            <span className="zh-platform-index">01</span><span className="zh-platform-symbol">◎</span>
            <h3>See the whole picture</h3><p>Begin with a global view, then move into the places that matter to your next decision.</p>
          </article>
          <article className="zh-platform-card">
            <span className="zh-platform-index">02</span><span className="zh-platform-symbol">⌖</span>
            <h3>Understand the region</h3><p>Explore country and regional context in the same geographic frame.</p>
          </article>
          <article className="zh-platform-card">
            <span className="zh-platform-index">03</span><span className="zh-platform-symbol">↗</span>
            <h3>Follow market signals</h3><p>Bring business conditions and available market data into one place.</p>
          </article>
        </div>
      </section>

      <section className="zh-category zh-reveal">
        <div className="zh-category-copy">
          <p className="zh-kicker">03 / A NEW WAY TO SEE MARKETS</p>
          <h2>A country is only<br />the first layer.</h2>
          <p className="zh-category-lede">A geographic model that keeps location at the center of the decision.</p>
          <a className="zh-arrow-link" href="#use-cases">See where Zetrix fits <span aria-hidden="true">↗</span></a>
        </div>
        <div className="zh-category-diagram" aria-label="Country and region view diagram">
          <div className="zh-diagram-orbit orbit-a" /><div className="zh-diagram-orbit orbit-b" />
          <div className="zh-diagram-node node-world"><span>WORLD</span></div>
          <div className="zh-diagram-node node-country"><span>COUNTRY</span></div>
          <div className="zh-diagram-node node-region"><span>REGION</span></div>
          <div className="zh-diagram-line line-a" /><div className="zh-diagram-line line-b" />
          <span className="zh-diagram-note">SCALE INTO THE DETAILS</span>
        </div>
      </section>

      <section className="zh-use-cases zh-reveal" id="use-cases">
        <div className="zh-use-heading">
          <div><p className="zh-kicker zh-kicker-light">04 / WHERE IT STARTS</p><h2>One world.<br /><em>Many reasons to look.</em></h2></div>
          <p>Whether you’re planning a move or evaluating a new market, start with the regional context that matters to you.</p>
        </div>
        <div className="zh-use-grid">
          <article className="zh-use-card">
            <span className="zh-use-number">01</span><span className="zh-use-mark">↗</span>
            <h3>Market expansion</h3><p>Compare the practical conditions behind potential business destinations.</p>
            <a href="/register" aria-label="Explore market expansion">Explore <span aria-hidden="true">↗</span></a>
          </article>
          <article className="zh-use-card">
            <span className="zh-use-number">02</span><span className="zh-use-mark">⌂</span>
            <h3>Property & place</h3><p>Use housing market data to add local context to location research.</p>
            <a href="/register" aria-label="Explore property and place">Explore <span aria-hidden="true">↗</span></a>
          </article>
          <article className="zh-use-card">
            <span className="zh-use-number">03</span><span className="zh-use-mark">◎</span>
            <h3>Living internationally</h3><p>Get oriented to regional rules, residency options, and everyday market signals.</p>
            <a href="/register" aria-label="Explore living internationally">Explore <span aria-hidden="true">↗</span></a>
          </article>
        </div>
      </section>

      <section className="zh-coverage zh-reveal" id="regions">
        <div className="zh-coverage-heading">
          <p className="zh-kicker">05 / COVERAGE</p><h2>Start anywhere.<br /><em>Go one level deeper.</em></h2>
          <p>Regional detail grows as data is reviewed and added. Open a country to see current coverage.</p>
        </div>
        <div className="zh-region-list">
          {regionalCountries.length ? regionalCountries.slice(0, 5).map((country) => (
            <button key={country.properties.iso2} className="zh-region-row" type="button" onClick={() => navigate(`/countries/${country.properties.iso2}`)}>
              <span className="zh-region-flag">{country.properties.flag_emoji}</span><span className="zh-region-name">{country.properties.name}</span>
              <span className="zh-region-meta">{country.properties.continent.name} · {country.properties.regions.length} {country.properties.regions.length === 1 ? "region" : "regions"}</span><span className="zh-region-arrow">↗</span>
            </button>
          )) : <p className="zh-no-regions">{loading ? "Loading regional coverage…" : "Regional coverage is being expanded."}</p>}
          <div className="zh-coverage-note"><span>{countries.length ? supportedHousing : "—"} housing markets</span><span>{listings ? `${listings.toLocaleString()} listings in current snapshot` : "Explore available country data"}</span></div>
        </div>
      </section>

      <section className="zh-contact zh-reveal" id="contact">
        <div className="zh-contact-inner">
          <p className="zh-kicker zh-kicker-light">THE NEXT DECISION STARTS WITH A PLACE</p>
          <h2>See the place<br />behind the <em>possibility.</em></h2>
          <a className="zh-button zh-button-light" href="/register">Get early access <span aria-hidden="true">↗</span></a>
          <div className="zh-contact-coordinate">ZETRIX / GLOBAL OPPORTUNITY EXPLORER</div>
        </div>
        <div className="zh-contact-orbit" aria-hidden="true"><span /><span /><span /></div>
      </section>
    </main>
  )
}
