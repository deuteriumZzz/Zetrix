import api from './client'

export const login = (username: string, password: string) =>
  api.post('/auth/token/', { username, password }).then((r) => r.data)

export const getAggregates = () =>
  api.get('/prices/aggregates/', {
    params: { market_type: 'rental', ordering: '-date', page_size: 100 },
  }).then((r) => r.data.results as Aggregate[])

export const getTrend = (countryIso2: string, regionId: string | null, days = 30) =>
  api.get('/prices/records/trend/', {
    params: { country: countryIso2, region: regionId ?? undefined, market_type: 'rental', days },
  }).then((r) => r.data as TrendPoint[])

export const getBusinessClimate = (countryIso2: string, regionId: string | null) =>
  api.get(`/opportunity/countries/${countryIso2}/`, {
    params: { region: regionId ?? undefined },
  }).then((r) => r.data as BusinessClimateProfile).catch(() => null)

export const getSources = () =>
  api.get('/sources/').then((r) => r.data)

export const getReports = () =>
  api.get('/reports/').then((r) => r.data.results as Report[])

export const createReport = (countryId: string, regionId: string | null, label: string) => {
  const today = new Date()
  const from = new Date(today)
  from.setDate(from.getDate() - 30)
  return api.post('/reports/', {
    title: `Market Report — ${label} (30d)`,
    country: countryId,
    region: regionId,
    market_type: 'rental',
    date_from: from.toISOString().slice(0, 10),
    date_to: today.toISOString().slice(0, 10),
    format: 'pdf',
  }).then((r) => r.data as Report)
}

export const getSubscriptions = () =>
  api.get('/notifications/subscriptions/').then((r) => r.data.results as Subscription[])

export const createSubscription = (countryId: string, regionId: string | null, threshold = 5) =>
  api.post('/notifications/subscriptions/', {
    country: countryId,
    region: regionId,
    market_type: 'rental',
    threshold_pct: threshold,
    direction: 'any',
  }).then((r) => r.data as Subscription)

export const deleteSubscription = (id: string) =>
  api.delete(`/notifications/subscriptions/${id}/`)

// Types
export interface Aggregate {
  id: string
  date: string
  country: string
  region: string | null
  market_type: string
  property_type: string
  avg_price_usd: string
  min_price_usd: string
  max_price_usd: string
  listings_count: number
  price_change_pct: string | null
}

export interface TrendPoint {
  date: string
  avg_price_usd: string
  price_change_pct: string | null
  listings_count: number
}

export interface BusinessClimateProfile {
  id: string
  country_iso2: string
  region: string | null
  foreign_land_ownership_summary: string
  foreign_land_ownership_score: number | null
  business_registration_summary: string
  business_registration_days_estimate: number | null
  business_registration_cost_usd_estimate: string | null
  business_registration_score: number | null
  tax_overview_summary: string
  corporate_tax_rate_pct: string | null
  personal_income_tax_top_rate_pct: string | null
  investor_visa_summary: string
  has_digital_nomad_visa: boolean
  has_investor_residency_program: boolean
  overall_complexity_score: number | null
  sources: { id: string; source_type: string; citation_url: string; raw_excerpt: string }[]
  last_reviewed_at: string | null
}

export interface Report {
  id: string
  title: string
  country: string | null
  region: string | null
  market_type: string
  date_from: string
  date_to: string
  status: string
  format: string
  file: string | null
  generated_at: string | null
  created_at: string
}

export interface Subscription {
  id: string
  country: string
  region: string | null
  market_type: string
  threshold_pct: string
  direction: string
  is_active: boolean
}
