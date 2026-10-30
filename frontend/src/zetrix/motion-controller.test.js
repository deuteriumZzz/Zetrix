import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest'
import { initializeMotion } from './motion'

const source = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8')
let cleanup
let reduced
let savedStorage
let observedAnimations
const element = id => document.getElementById(id)
beforeEach(() => {
  document.documentElement.innerHTML = source
  reduced = new EventTarget()
  reduced.matches = false
  vi.stubGlobal('matchMedia', query => query.includes('reduced') ? reduced : { matches: true })
  vi.stubGlobal('requestAnimationFrame', vi.fn(() => 1))
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
  vi.stubGlobal('IntersectionObserver', class { observe() {} unobserve() {} disconnect() {} })
  savedStorage = Object.getOwnPropertyDescriptor(window, 'localStorage')
  const data = new Map()
  Object.defineProperty(window, 'localStorage', { configurable: true, value: {
    getItem: key => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
  } })
  observedAnimations = []
  vi.stubGlobal('Animation', class {})
  Object.defineProperty(HTMLElement.prototype, 'animate', { configurable: true, value: vi.fn(() => {
    const animation = new EventTarget()
    animation.cancel = vi.fn()
    animation.pause = vi.fn()
    animation.play = vi.fn()
    observedAnimations.push(animation)
    return animation
  }) })
})
afterEach(() => {
  cleanup?.()
  cleanup = undefined
  delete HTMLElement.prototype.animate
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  if (savedStorage) Object.defineProperty(window, 'localStorage', savedStorage)
  else delete window.localStorage
})

describe('motion lifecycle', () => {
  it('pauses every animation system and remembers preference', () => {
    const pause = vi.fn()
    element('planet').addEventListener('zetrix:pause', pause)
    cleanup = initializeMotion()
    expect(document.documentElement.dataset.motion).toBe('full')
    element('motion-toggle').click()
    expect(document.documentElement.dataset.motion).toBe('paused')
    expect(element('pause-globe')).toBeDisabled()
    expect(pause.mock.calls.at(-1)[0].detail).toBe(true)
    expect(window.localStorage.getItem('zetrix:motion-paused:v1')).toBe('true')
    observedAnimations.forEach(animation => expect(animation.cancel).toHaveBeenCalled())
    cleanup()
    cleanup = initializeMotion()
    expect(document.documentElement.dataset.motion).toBe('paused')
  })
  it('respects system preference changes and preserves manual pause', () => {
    cleanup = initializeMotion()
    element('motion-toggle').click()
    reduced.matches = true
    reduced.dispatchEvent(new Event('change'))
    expect(document.documentElement.dataset.motion).toBe('reduced')
    expect(element('motion-toggle')).toBeDisabled()
    reduced.matches = false
    reduced.dispatchEvent(new Event('change'))
    expect(document.documentElement.dataset.motion).toBe('paused')
    expect(element('motion-toggle')).not.toBeDisabled()
  })
  it('skips decorative feedback for keyboard actions and removes listeners on cleanup', () => {
    cleanup = initializeMotion()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    const count = observedAnimations.length
    element('export-scenario').click()
    expect(observedAnimations).toHaveLength(count)
    cleanup()
    cleanup = undefined
    element('motion-toggle').click()
    expect(document.documentElement.dataset.motion).toBeUndefined()
  })
  it('pauses the globe while the document is hidden', () => {
    const pause = vi.fn()
    element('planet').addEventListener('zetrix:pause', pause)
    cleanup = initializeMotion()
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    document.dispatchEvent(new Event('visibilitychange'))
    expect(document.documentElement.dataset.pageHidden).toBe('true')
    expect(pause.mock.calls.at(-1)[0].detail).toBe(true)
  })
})
