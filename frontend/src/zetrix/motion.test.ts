import { describe, expect, it } from 'vitest'
import { clamp, scrollFraction, motionMode } from './motion-utils'

describe('motion state and scroll boundaries', () => {
  it('clamps overscroll and short documents', () => {
    expect(scrollFraction(-50, 2000, 800)).toBe(0)
    expect(scrollFraction(600, 2000, 800)).toBe(0.5)
    expect(scrollFraction(5000, 2000, 800)).toBe(1)
    expect(scrollFraction(10, 600, 800)).toBe(0)
    expect(clamp(2)).toBe(1)
  })
  it('always respects system reduced motion over stored preferences', () => {
    expect(motionMode(true, false)).toBe('reduced')
    expect(motionMode(true, true)).toBe('reduced')
    expect(motionMode(false, true)).toBe('paused')
    expect(motionMode(false, false)).toBe('full')
  })
})
