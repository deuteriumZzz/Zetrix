import { describe, expect, it } from 'vitest'
import { comparisonIssue, formatMoney } from './domain'
import type { Run } from './types'
const run = (id: string, months = 3, monthly_cost = '1000000.00') => ({ id, inputs: { months, monthly_cost, currency: 'USD' }, results: { baseline_total: '3000000.00' }, engine_version: 'v1' } as Run)
describe('result presentation', () => {
  it('retains cents without binary-number conversion', () => expect(formatMoney('1234567890.01')).toBe('1 234 567 890,01 USD'))
  it('allows shared baselines and blocks incompatible comparisons', () => {
    expect(comparisonIssue([run('1'), run('2')])).toBeNull()
    expect(comparisonIssue([run('1'), run('2', 6)])).toContain('горизонт')
    expect(comparisonIssue([run('1'), run('2', 3, '2000000.00')])).toContain('базовые')
  })
})
