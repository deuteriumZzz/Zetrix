export type ScenarioKind = 'trade' | 'supply' | 'energy'
export interface ScenarioInput {
  kind: ScenarioKind
  monthlyCost: number
  exposure: number
  shock: number
  months: number
}
export const presets: Record<ScenarioKind, Readonly<ScenarioInput>> = {
  trade: { kind: 'trade', monthlyCost: 1000000, exposure: 35, shock: 20, months: 3 },
  supply: { kind: 'supply', monthlyCost: 250000, exposure: 60, shock: 30, months: 3 },
  energy: { kind: 'energy', monthlyCost: 150000, exposure: 80, shock: 40, months: 3 },
}
export const scenarioCopy: Record<ScenarioKind, { title: string; cost: string; shock: string; explanation: string }> = {
  trade: { title: 'Торговые ограничения', cost: 'Месячные затраты на импорт', shock: 'Удорожание затронутого импорта', explanation: 'Рост стоимости затронутого импорта увеличивает закупочный бюджет. Проверьте возможность замены поставщиков и пересмотра условий.' },
  supply: { title: 'Перебои поставок', cost: 'Месячные логистические затраты', shock: 'Удорожание затронутых перевозок', explanation: 'Альтернативные маршруты могут увеличить расходы на доставку. Сравните этот сценарий с условиями ваших перевозчиков. Потери от задержек здесь не учтены.' },
  energy: { title: 'Энергетический шок', cost: 'Месячные энергозатраты', shock: 'Удорожание затронутой энергии', explanation: 'Удорожание энергии увеличивает операционные расходы. Проверьте долю затрат, защищённую фиксированными контрактами. Изменение объёмов производства не учтено.' },
}
export function parseScenario(value: unknown): ScenarioInput | null {
  if (!value || typeof value !== 'object') return null
  const v = value as Record<string, unknown>
  if (v.kind !== 'trade' && v.kind !== 'supply' && v.kind !== 'energy') return null
  const bounds: Array<[string, number, number]> = [['monthlyCost', 1, 1e9], ['exposure', 0, 100], ['shock', 0, 100], ['months', 1, 12]]
  if (bounds.some(([key, min, max]) => typeof v[key] !== 'number' || !Number.isFinite(v[key]) || (v[key] as number) < min || (v[key] as number) > max || !Number.isInteger(v[key]))) return null
  if (![1, 3, 6, 12].includes(v.months as number)) return null
  return { kind: v.kind, monthlyCost: v.monthlyCost as number, exposure: v.exposure as number, shock: v.shock as number, months: v.months as number }
}
export function calculateScenario(input: ScenarioInput) {
  if (!parseScenario(input)) throw new RangeError('Invalid scenario inputs')
  const exposedMonthly = input.monthlyCost * input.exposure / 100
  const additionalMonthly = exposedMonthly * input.shock / 100
  const baselineTotal = input.monthlyCost * input.months
  const additionalTotal = additionalMonthly * input.months
  return { exposedMonthly, additionalMonthly, additionalTotal, baselineTotal, scenarioTotal: baselineTotal + additionalTotal, increasePercent: input.exposure * input.shock / 100 }
}
export const modelAssumptions = [
  'Учебная модель прямого воздействия на затраты; не AI-прогноз и не оценка вероятности события.',
  'Источник параметров: пользователь. Начальные значения иллюстративные.',
  'Объёмы, доля затронутых затрат и удорожание постоянны на всём горизонте.',
  'Валютные изменения, реакция спроса, запасы, налоги и вторичные эффекты отдельно не моделируются.',
  'Дополнительные затраты = месячные затраты × доля / 100 × удорожание / 100 × число месяцев.',
]
