import api from './client'

export const login = (username: string, password: string) =>
  api.post('/auth/token/', { username, password }).then((r) => r.data)

export const register = (username: string, email: string, password: string) =>
  api.post('/users/register/', { username, email, password }).then((r) => r.data)

export const requestPasswordReset = (email: string) =>
  api.post('/users/password-reset/', { email }).then((r) => r.data)

export const confirmPasswordReset = (uid: string, token: string, newPassword: string) =>
  api
    .post('/users/password-reset/confirm/', { uid, token, new_password: newPassword })
    .then((r) => r.data)

export interface UserProfile {
  id: string
  username: string
  email: string
  telegram_chat_id: string | null
  telegram_username: string
  preferred_country: string | null
  preferred_region: string | null
  preferred_market_type: string
}

export const getProfile = () =>
  api.get('/users/me/').then((r) => r.data as UserProfile)

export const updateProfile = (data: Partial<UserProfile>) =>
  api.patch('/users/me/', data).then((r) => r.data as UserProfile)

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

export const retryReport = (id: string) =>
  api.post(`/reports/${id}/retry/`).then((r) => r.data)

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

export interface Plan {
  id: string
  name: string
  slug: string
  price_usd_monthly: string
  max_active_alerts: number
  max_reports_per_month: number
  business_climate_access: boolean
}

export const getPlans = () =>
  api.get('/billing/plans/').then((r) => r.data as Plan[])

export const getMyPlan = () =>
  api.get('/billing/me/').then((r) => r.data as { plan: Plan; subscription: unknown | null })

export const createCheckoutSession = (planId: string) =>
  api.post('/billing/checkout/', { plan_id: planId }).then((r) => r.data as { checkout_url: string })

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
  country_name: string
  country_flag: string
  region: string | null
  region_name: string | null
  market_type: string
  threshold_pct: string
  direction: string
  is_active: boolean
}
