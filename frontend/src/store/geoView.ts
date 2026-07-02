import { create } from 'zustand'

export type Layer = 'housing' | 'business'

interface GeoViewState {
  activeLayer: Layer
  setLayer: (layer: Layer) => void
}

export const useGeoViewStore = create<GeoViewState>((set) => ({
  activeLayer: 'housing',
  setLayer: (activeLayer) => set({ activeLayer }),
}))
