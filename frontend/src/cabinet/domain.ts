import type { Inputs, Run } from './types'
export const initialInputs: Inputs = { kind: 'trade', monthly_cost: '1000000.00', exposure: '35.00', shock: '20.00', months: 3, currency: 'USD' }
export const kindNames = { trade: 'Торговые ограничения', supply: 'Сбой поставок', energy: 'Энергетический шок' }
export const roleNames = { owner: 'Владелец', admin: 'Администратор', analyst: 'Аналитик', viewer: 'Наблюдатель' }
export function formatMoney(value: string) {
  const [whole, fraction = '00'] = value.split('.')
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')},${fraction.padEnd(2, '0')} USD`
}
export const dateLabel = (date: string) => new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(date))
const normalized = (value: string) => value.replace(/^0+(?=\d)/, '').replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1')
export function comparisonIssue(runs: Run[]): string | null {
  if (runs.length < 2) return 'Выберите минимум два результата.'
  const first = runs[0]
  if (runs.some(run => run.project_id !== first.project_id)) return 'Для сравнения нужны расчёты одного проекта.'
  if (runs.some(run => run.inputs.kind !== first.inputs.kind)) return 'Для сравнения нужен одинаковый тип воздействия.'
  if (runs.some(run => run.context?.portfolio_revision_id !== first.context?.portfolio_revision_id)) return 'Для сравнения нужна одна версия закупочного портфеля.'
  if (runs.some(run => run.inputs.currency !== first.inputs.currency)) return 'Для сравнения нужна одна валюта.'
  if (runs.some(run => run.inputs.months !== first.inputs.months)) return 'Для сравнения нужен одинаковый горизонт.'
  if (runs.some(run => normalized(run.inputs.monthly_cost) !== normalized(first.inputs.monthly_cost) || normalized(run.results.baseline_total) !== normalized(first.results.baseline_total))) return 'Для сравнения нужны одинаковые базовые затраты.'
  if (runs.some(run => run.engine_version !== first.engine_version)) return 'Версии расчётной модели должны совпадать.'
  return null
}
export const canWrite = (role?: string) => ['owner', 'admin', 'analyst'].includes(role || '')
