import { describe, expect, it } from 'vitest'
import { calculateScenario, parseScenario, presets } from './scenario'

describe('transparent scenario cost model', () => {
  it('applies the shock only to exposed costs across the selected horizon', () => {
    expect(calculateScenario({ kind: 'trade', monthlyCost: 1000000, exposure: 35, shock: 20, months: 3 })).toEqual({
      exposedMonthly: 350000, additionalMonthly: 70000, additionalTotal: 210000,
      baselineTotal: 3000000, scenarioTotal: 3210000, increasePercent: 7,
    })
  })
  it('handles no exposure and maximum exposure without hidden multipliers', () => {
    expect(calculateScenario({ ...presets.trade, exposure: 0 }).additionalTotal).toBe(0)
    expect(calculateScenario({ ...presets.trade, exposure: 100, shock: 100, months: 1 }).additionalTotal).toBe(presets.trade.monthlyCost)
  })
  it('rejects corrupt saved data and invalid numeric boundaries', () => {
    for (const value of [null, {}, { ...presets.trade, kind: 'unknown' }, { ...presets.trade, monthlyCost: NaN }, { ...presets.trade, exposure: -1 }, { ...presets.trade, shock: 101 }, { ...presets.trade, months: 1.5 }, { ...presets.trade, monthlyCost: 1000000001 }]) {
      expect(parseScenario(value)).toBeNull()
    }
    expect(parseScenario(presets.supply)).toEqual(presets.supply)
  })
  it('does not accept invalid model inputs or mutate the input', () => {
    const input = Object.freeze({ ...presets.energy })
    expect(calculateScenario(input).additionalTotal).toBeGreaterThan(0)
    expect(() => calculateScenario({ ...presets.trade, months: 0 })).toThrow()
  })
})
