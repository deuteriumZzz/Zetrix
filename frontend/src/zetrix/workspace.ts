import { calculateScenario, modelAssumptions, parseScenario, presets, scenarioCopy, type ScenarioInput, type ScenarioKind } from './scenario'
import { downloadJson } from './download'

const storageKey = 'zetrix:scenario:v1'
const currency = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 })
const percent = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 })
const money = (value: number) => `$${currency.format(value)}`

export function initializeWorkspace(): () => void {
  const abort = new AbortController()
  const options = { signal: abort.signal }
  const get = <T extends HTMLElement>(id: string) => document.getElementById(id) as T
  const form = get<HTMLFormElement>('scenario-form')
  const tabs = [...document.querySelectorAll<HTMLButtonElement>('[data-scenario]')]
  const controls = ['monthly-cost', 'exposure', 'shock', 'months'].map(id => get<HTMLInputElement | HTMLSelectElement>(id))
  const [cost, exposure, shock, months] = controls
  let state: ScenarioInput = { ...presets.trade }
  const drafts: Partial<Record<ScenarioKind, ScenarioInput>> = {}
  const status = (message: string) => { get('save-status').textContent = message }
  const input = () => parseScenario({ kind: state.kind, monthlyCost: Number(cost.value), exposure: Number(exposure.value), shock: Number(shock.value), months: Number(months.value) })

  function render() {
    const result = calculateScenario(state)
    const copy = scenarioCopy[state.kind]
    get('cost-label').textContent = copy.cost
    get('shock-label').textContent = copy.shock
    get('exposure-value').textContent = `${state.exposure}%`
    get('shock-value').textContent = `${state.shock}%`
    get('result-horizon').textContent = `ЗА ${state.months} МЕС.`
    get('additional-total').textContent = `+${money(result.additionalTotal)}`
    get('increase-percent').textContent = `+${percent.format(result.increasePercent)}%`
    get('baseline-total').textContent = money(result.baselineTotal)
    get('scenario-total').textContent = money(result.scenarioTotal)
    get('scenario-description').textContent = copy.explanation
    get('baseline-bar').style.transform = `scaleX(${result.baselineTotal / result.scenarioTotal})`
    get('extra-bar').style.transform = `scaleX(${result.additionalTotal / result.scenarioTotal})`
    get('comparison-chart').setAttribute('aria-label', `Исходный бюджет ${money(result.baselineTotal)}, при сценарии ${money(result.scenarioTotal)}`)
    get('scenario-panel').setAttribute('aria-labelledby', `tab-${state.kind}`)
    document.querySelector<HTMLElement>('.scenario-tabs')?.style.setProperty('--active-tab', String(tabs.findIndex(tab => tab.dataset.scenario === state.kind)))
    document.dispatchEvent(new CustomEvent('zetrix:scenario', { detail: { kind: state.kind } }))
    tabs.forEach(tab => {
      const selected = tab.dataset.scenario === state.kind
      tab.setAttribute('aria-selected', String(selected))
      tab.tabIndex = selected ? 0 : -1
    })
  }
  function load(next: ScenarioInput) {
    state = { ...next }
    ;[cost.value, exposure.value, shock.value, months.value] = [state.monthlyCost, state.exposure, state.shock, state.months].map(String)
    get('input-error').textContent = ''
    cost.removeAttribute('aria-invalid')
    get<HTMLButtonElement>('export-scenario').disabled = false
    get<HTMLButtonElement>('save-scenario').disabled = false
    render()
  }
  function update() {
    const next = input()
    const valid = next !== null && form.checkValidity()
    get('input-error').textContent = valid ? '' : 'Укажите целые месячные затраты от $1 до $1 млрд. Результат пока не обновлён.'
    cost.setAttribute('aria-invalid', String(!valid))
    get<HTMLButtonElement>('export-scenario').disabled = !valid
    get<HTMLButtonElement>('save-scenario').disabled = !valid
    if (!valid || !next) return
    state = next
    drafts[state.kind] = { ...state }
    render()
    status('Изменения не сохранены')
  }
  form.addEventListener('submit', event => event.preventDefault(), options)
  form.addEventListener('input', update, options)
  form.addEventListener('change', update, options)
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => {
      const kind = tab.dataset.scenario as ScenarioKind
      drafts[state.kind] = { ...state }
      load(drafts[kind] ?? presets[kind])
      status('Сценарий можно сохранить на этом устройстве')
    }, options)
    tab.addEventListener('keydown', event => {
      const nextIndex = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null
      if (nextIndex === null) return
      event.preventDefault()
      tabs[nextIndex].focus()
      tabs[nextIndex].click()
    }, options)
  })
  get('save-scenario').addEventListener('click', () => {
    if (!input() || !form.checkValidity()) return
    try { window.localStorage.setItem(storageKey, JSON.stringify(state)); status('Сценарий сохранён на этом устройстве') }
    catch { status('Браузер не разрешил сохранение. Скачайте расчёт в файл.') }
  }, options)
  get('reset-scenario').addEventListener('click', () => {
    load(presets[state.kind])
    drafts[state.kind] = { ...state }
    try { window.localStorage.removeItem(storageKey); status('Начальные значения восстановлены. Сохранённый сценарий удалён.') }
    catch { status('Начальные значения восстановлены. Не удалось удалить сохранение браузера.') }
  }, options)
  get('export-scenario').addEventListener('click', () => {
    if (!input() || !form.checkValidity()) return
    try {
      downloadJson(`zetrix-${state.kind}-scenario.json`, { product: 'Zetrix', model: 'cost-exposure-v1', demo: true, currency: 'USD', createdAt: new Date().toISOString(), scenario: scenarioCopy[state.kind].title, inputs: state, results: calculateScenario(state), assumptions: modelAssumptions })
      status('Файл расчёта подготовлен к скачиванию')
    } catch { status('Не удалось скачать файл. Попробуйте ещё раз.') }
  }, options)
  try {
    const saved = window.localStorage.getItem(storageKey)
    const parsed = saved ? parseScenario(JSON.parse(saved)) : null
    if (parsed) { load(parsed); status('Восстановлен ваш сохранённый сценарий') }
    else { load(state); if (saved) status('Сохранение не распознано. Загружен учебный пример.') }
  } catch { load(state); status('Сохранение недоступно. Вы можете скачать расчёт.') }
  return () => abort.abort()
}
