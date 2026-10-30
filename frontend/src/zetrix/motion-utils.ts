export const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value))
export function scrollFraction(scroll: number, height: number, viewport: number): number {
  return height <= viewport ? 0 : clamp(scroll / (height - viewport))
}
export function motionMode(reduced: boolean, paused: boolean): 'full' | 'reduced' | 'paused' {
  return reduced ? 'reduced' : paused ? 'paused' : 'full'
}
