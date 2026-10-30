import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { JSDOM } from 'jsdom'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { initializeWorkspace } from './workspace'
import { downloadJson } from './download'
vi.mock('./download', () => ({ downloadJson: vi.fn() }))
const source = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8')
let cleanup
let storageDOM
let originalStorage
const element = id => document.getElementById(id)
const setValue = (id, value) => { element(id).value = String(value); element(id).dispatchEvent(new Event('input', { bubbles: true })) }
beforeEach(() => {
  document.documentElement.innerHTML = source
  // Node's built-in localStorage can shadow Vitest 1's jsdom storage.
  // Use real browser storage from an isolated, non-opaque jsdom origin.
  storageDOM = new JSDOM('', { url: 'https://zetrix.test/' })
  originalStorage = Object.getOwnPropertyDescriptor(window, 'localStorage')
  Object.defineProperty(window, 'localStorage', { configurable: true, value: storageDOM.window.localStorage })
  cleanup = undefined
  vi.clearAllMocks()
})
afterEach(() => {
  cleanup?.()
  vi.restoreAllMocks()
  if (originalStorage) Object.defineProperty(window, 'localStorage', originalStorage)
  else delete window.localStorage
  storageDOM.window.close()
})

describe('Zetrix scenario workspace', () => {
  it('keeps brand and navigation local, with no reference-company media', () => {
    expect(source).not.toMatch(/anadyr|harvard|wixstatic|hubspot/i)
    for (const link of document.querySelectorAll('a[href^="#"]')) {
      const href = link.getAttribute('href')
      if (href.length > 1) expect(document.querySelector(href)).not.toBeNull()
    }
  })
  it('updates calculations, switches scenarios and retains per-tab inputs', () => {
    cleanup = initializeWorkspace()
    setValue('monthly-cost', 2000000)
    expect(element('additional-total').textContent.replace(/\s/g, '')).toBe('+$420000')
    element('tab-supply').click()
    expect(element('cost-label')).toHaveTextContent('логистические')
    expect(element('additional-total').textContent.replace(/\s/g, '')).toBe('+$135000')
    element('tab-trade').click()
    expect(element('monthly-cost').value).toBe('2000000')
  })
  it('does not export invalid values or overwrite the last valid result', () => {
    cleanup = initializeWorkspace()
    setValue('monthly-cost', -1)
    expect(element('export-scenario')).toBeDisabled()
    expect(element('save-scenario')).toBeDisabled()
    expect(element('input-error')).toHaveTextContent('Результат пока не обновлён')
    expect(element('additional-total').textContent.replace(/\s/g, '')).toBe('+$210000')
    setValue('monthly-cost', 1)
    setValue('exposure', 0)
    expect(element('export-scenario')).not.toBeDisabled()
    expect(element('additional-total')).toHaveTextContent('+$0')
  })
  it('restores validated saved data and exports model assumptions', () => {
    cleanup = initializeWorkspace()
    element('tab-energy').click()
    element('save-scenario').click()
    cleanup()
    cleanup = initializeWorkspace()
    expect(element('tab-energy')).toHaveAttribute('aria-selected', 'true')
    expect(element('save-status')).toHaveTextContent('Восстановлен')
    element('export-scenario').click()
    expect(downloadJson).toHaveBeenCalledWith('zetrix-energy-scenario.json', expect.objectContaining({ demo: true, currency: 'USD', assumptions: expect.any(Array), results: expect.objectContaining({ additionalTotal: 144000 }) }))
  })
  it('recovers from corrupt storage and permits keyboard tab navigation', () => {
    window.localStorage.setItem('zetrix:scenario:v1', '{broken')
    cleanup = initializeWorkspace()
    expect(element('monthly-cost').value).toBe('1000000')
    element('tab-trade').dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }))
    expect(element('tab-energy')).toHaveAttribute('aria-selected', 'true')
    expect(document.activeElement).toBe(element('tab-energy'))
    element('reset-scenario').click()
    expect(window.localStorage.getItem('zetrix:scenario:v1')).toBeNull()
  })
  it('reports unavailable storage while leaving exports functional', () => {
    cleanup = initializeWorkspace()
    vi.spyOn(storageDOM.window.Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Storage blocked') })
    element('save-scenario').click()
    expect(element('save-status')).toHaveTextContent('не разрешил сохранение')
    element('export-scenario').click()
    expect(downloadJson).toHaveBeenCalledOnce()
  })
})
