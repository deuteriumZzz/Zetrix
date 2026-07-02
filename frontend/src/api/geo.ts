import api from './client'

export interface GeoRegion {
  id: string
  name: string
  slug: string
  level: string
  parent: string | null
  centroid_lat: number
  centroid_lng: number
}

export interface GeoCountryProperties {
  iso2: string
  iso3: string
  name: string
  continent: { id: string; code: string; name: string; slug: string }
  centroid_lat: number
  centroid_lng: number
  currency_code: string
  flag_emoji: string
  is_housing_supported: boolean
  regions: GeoRegion[]
}

export interface GeoCountry {
  type: 'Feature'
  id: string
  geometry: unknown
  properties: GeoCountryProperties
}

export interface Continent {
  id: string
  code: string
  name: string
  slug: string
}

export const getContinents = () =>
  api.get('/geo/continents/').then((r) => r.data as Continent[])

export const getCountries = () =>
  api.get('/geo/countries/').then((r) => r.data.features as GeoCountry[])

export const getCountry = (iso2: string) =>
  api.get(`/geo/countries/${iso2}/`).then((r) => r.data as GeoCountry)
