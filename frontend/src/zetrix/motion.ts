import { clamp, motionMode, scrollFraction } from './motion-utils'

const EASE_OUT = 'cubic-bezier(.22,1,.36,1)'
const preferenceKey = 'zetrix:motion-paused:v1'

/** Decorative motion never changes model values, focus order, or document scrolling. */
export function initializeMotion(): () => void {
  const root = document.documentElement
  const lifecycle = new AbortController()
  const options = { signal: lifecycle.signal }
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)')
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)')
  const animations = new Set<Animation>()
  const running = new WeakMap<Element, Animation>()
  const observers: Array<{ disconnect(): void }> = []
  const canvas = document.getElementById('planet')!
  const toggle = document.getElementById('motion-toggle') as HTMLButtonElement
  const globeToggle = document.getElementById('pause-globe') as HTMLButtonElement
  const hero = document.querySelector<HTMLElement>('.hero')!
  const globe = document.querySelector<HTMLElement>('.globe-stage')!
  const grid = document.querySelector<HTMLElement>('.hero-grid')!
  const glow = document.querySelector<HTMLElement>('.pointer-light')!
  const progress = document.getElementById('page-progress-fill')!
  const dockLinks = [...document.querySelectorAll<HTMLAnchorElement>('.chapter-dock a')]
  const chapters = dockLinks.map(link => document.querySelector<HTMLElement>(link.hash)!)
  const pointerElements = [...document.querySelectorAll<HTMLElement>('.button, .principle-grid article, .use-case-list article')]
  let userPaused = false
  let globePaused = false
  let scrollFrame = 0
  let disposed = false
  let lastScenario = document.querySelector('[role=tab][aria-selected=true]')?.getAttribute('data-scenario')
  try { userPaused = window.localStorage.getItem(preferenceKey) === 'true' } catch { /* Motion preferences are optional. */ }
  const enabled = () => root.dataset.motion === 'full' && !document.hidden
  const interactive = () => enabled() && root.dataset.inputMode !== 'keyboard'

  function play(element: HTMLElement, frames: Keyframe[], duration = 240, delay = 0) {
    if (!interactive() || typeof element.animate !== 'function') return
    running.get(element)?.cancel()
    const animation = element.animate(frames, { duration, delay, easing: EASE_OUT, fill: 'backwards' })
    running.set(element, animation)
    animations.add(animation)
    const remove = () => animations.delete(animation)
    animation.addEventListener('finish', remove, { once: true })
    animation.addEventListener('cancel', remove, { once: true })
  }
  function enter(element: HTMLElement, delay = 0) {
    play(element, [{ opacity: 0, transform: 'translateY(20px)' }, { opacity: 1, transform: 'translateY(0)' }], 650, delay)
  }
  function syncGlobe() {
    const stopped = !enabled() || globePaused
    globeToggle.disabled = root.dataset.motion !== 'full'
    globeToggle.setAttribute('aria-pressed', String(stopped))
    globeToggle.setAttribute('aria-label', globeToggle.disabled ? 'Вращение отключено общими настройками анимации' : stopped ? 'Продолжить вращение глобуса' : 'Приостановить вращение глобуса')
    globeToggle.textContent = stopped ? '▷' : 'Ⅱ'
    canvas.dispatchEvent(new CustomEvent('zetrix:pause', { detail: stopped }))
  }
  function clearTransforms() {
    globe.style.removeProperty('transform')
    grid.style.removeProperty('transform')
    pointerElements.forEach(element => { element.style.removeProperty('translate'); element.style.removeProperty('rotate') })
    glow.style.opacity = '0'
  }
  function applyPreference() {
    root.dataset.motion = motionMode(reduced.matches, userPaused)
    toggle.disabled = reduced.matches
    toggle.setAttribute('aria-pressed', String(root.dataset.motion !== 'full'))
    toggle.setAttribute('aria-label', reduced.matches ? 'Анимация ограничена настройками системы' : userPaused ? 'Включить декоративные анимации' : 'Приостановить все декоративные анимации')
    toggle.querySelector('.motion-switch-label')!.textContent = reduced.matches ? 'Меньше движения' : userPaused ? 'Анимация: выкл.' : 'Анимация: вкл.'
    toggle.querySelector('.motion-switch-icon')!.textContent = root.dataset.motion === 'full' ? 'Ⅱ' : '▷'
    if (!enabled()) {
      animations.forEach(animation => animation.cancel())
      animations.clear()
      clearTransforms()
    }
    syncGlobe()
    scheduleScroll()
  }
  function renderScroll() {
    scrollFrame = 0
    if (disposed || document.hidden) return
    progress.style.transform = `scaleX(${scrollFraction(window.scrollY, root.scrollHeight, window.innerHeight)})`
    let active = 0
    chapters.forEach((section, index) => { if (section.getBoundingClientRect().top <= window.innerHeight * 0.45) active = index })
    dockLinks.forEach((link, index) => {
      if (index === active) link.setAttribute('aria-current', 'location')
      else link.removeAttribute('aria-current')
    })
    if (!enabled() || window.innerWidth < 761) { globe.style.removeProperty('transform'); grid.style.removeProperty('transform'); return }
    const bounds = hero.getBoundingClientRect()
    if (bounds.bottom < 0) return
    const amount = clamp(-bounds.top / bounds.height)
    globe.style.transform = `translate3d(0,${amount * 55}px,0) scale(${1 + amount * .045})`
    grid.style.transform = `translate3d(0,${-amount * 38}px,0)`
  }
  function scheduleScroll() {
    if (!disposed && !scrollFrame && !document.hidden) scrollFrame = requestAnimationFrame(renderScroll)
  }
  document.addEventListener('keydown', () => { root.dataset.inputMode = 'keyboard' }, options)
  document.addEventListener('pointerdown', () => { root.dataset.inputMode = 'pointer' }, options)
  toggle.addEventListener('click', () => {
    userPaused = !userPaused
    try { window.localStorage.setItem(preferenceKey, String(userPaused)) } catch { /* Current-session control remains usable. */ }
    applyPreference()
  }, options)
  globeToggle.addEventListener('click', () => { globePaused = !globePaused; syncGlobe() }, options)
  reduced.addEventListener('change', applyPreference, options)
  document.addEventListener('visibilitychange', () => {
    root.dataset.pageHidden = String(document.hidden)
    if (document.hidden) animations.forEach(animation => animation.pause())
    else animations.forEach(animation => { if (enabled()) animation.play() })
    syncGlobe()
    scheduleScroll()
  }, options)
  window.addEventListener('scroll', scheduleScroll, { ...options, passive: true })
  window.addEventListener('resize', scheduleScroll, options)

  function observeSections() {
    if (!('IntersectionObserver' in window)) return
    const reveal = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return
        const element = entry.target as HTMLElement
        element.classList.add('in-view')
        enter(element)
        reveal.unobserve(element)
      })
    }, { threshold: .12 })
    document.querySelectorAll<HTMLElement>('.reveal').forEach(element => reveal.observe(element))
    observers.push(reveal)
    const visibility = new IntersectionObserver(entries => {
      entries.forEach(entry => (entry.target as HTMLElement).dataset.motionVisible = String(entry.isIntersecting))
    }, { threshold: 0 })
    document.querySelectorAll('.hero, .signal-strip, .reaction-chain, .pilot-section').forEach(element => visibility.observe(element))
    observers.push(visibility)
    const groups = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return
        entry.target.querySelectorAll<HTMLElement>('article').forEach((element, index) => enter(element, index * 70))
        groups.unobserve(entry.target)
      })
    }, { threshold: .15 })
    document.querySelectorAll('.reaction-chain, .principle-grid, .use-case-list').forEach(group => groups.observe(group))
    observers.push(groups)
  }
  function bindPointerEffects() {
    hero.addEventListener('pointermove', event => {
      if (!enabled() || !finePointer.matches) return
      const bounds = hero.getBoundingClientRect()
      glow.style.transform = `translate3d(${event.clientX - bounds.left - 170}px,${event.clientY - bounds.top - 170}px,0)`
      glow.style.opacity = '.65'
    }, { ...options, passive: true })
    hero.addEventListener('pointerleave', () => { glow.style.opacity = '0' }, options)
    pointerElements.forEach(element => {
      element.addEventListener('pointermove', event => {
        if (!interactive() || !finePointer.matches) return
        const bounds = element.getBoundingClientRect()
        const x = (event.clientX - bounds.left) / bounds.width - .5
        const y = (event.clientY - bounds.top) / bounds.height - .5
        if (element.classList.contains('button')) element.style.translate = `${x * 6}px ${y * 6}px`
        else element.style.rotate = `${-y} ${x} 0 1.4deg`
      }, { ...options, passive: true })
      element.addEventListener('pointerleave', () => { element.style.removeProperty('translate'); element.style.removeProperty('rotate') }, options)
    })
  }
  function bindUIEffects() {
    const dialog = document.getElementById('brief-dialog') as HTMLDialogElement
    const menu = document.getElementById('navigation')!
    const mutation = new MutationObserver(records => {
      records.forEach(record => {
        if (record.target === dialog && dialog.open) play(dialog, [{ opacity: 0, transform: 'translateY(14px) scale(.975)' }, { opacity: 1, transform: 'translateY(0) scale(1)' }], 260)
        if (record.target === menu && menu.dataset.open === 'true') play(menu, [{ opacity: 0, transform: 'translateY(-8px) scale(.98)' }, { opacity: 1, transform: 'translateY(0) scale(1)' }], 190)
      })
    })
    mutation.observe(dialog, { attributes: true, attributeFilter: ['open'] })
    mutation.observe(menu, { attributes: true, attributeFilter: ['data-open'] })
    observers.push(mutation)
    document.addEventListener('zetrix:scenario', event => {
      const kind = (event as CustomEvent<{ kind: string }>).detail.kind
      const target = document.getElementById('additional-total')!
      play(target, [{ opacity: .55, transform: 'translateY(5px)' }, { opacity: 1, transform: 'translateY(0)' }], 200)
      if (kind !== lastScenario) {
        play(document.querySelector<HTMLElement>('.scenario-observation')!, [{ opacity: .1, transform: 'translateX(9px)' }, { opacity: 1, transform: 'translateX(0)' }], 230)
        lastScenario = kind
      }
    }, options)
    document.querySelectorAll<HTMLElement>('.quiet-button, .export-button').forEach(button => {
      button.addEventListener('click', () => play(button, [{ transform: 'scale(.96)' }, { transform: 'scale(1)' }], 160), options)
    })
    const details = document.querySelector<HTMLDetailsElement>('.model-notes')!
    details.addEventListener('toggle', () => {
      if (details.open) play(details.querySelector<HTMLElement>('.notes-grid')!, [{ opacity: 0, transform: 'translateY(-5px)' }, { opacity: 1, transform: 'translateY(0)' }], 230)
      scheduleScroll()
    }, options)
  }
  root.dataset.pageHidden = String(document.hidden)
  applyPreference()
  observeSections()
  bindPointerEffects()
  bindUIEffects()
  document.querySelectorAll<HTMLElement>('.hero-line > *').forEach((element, index) => {
    play(element, [{ transform: 'translateY(112%) rotate(2deg)', opacity: .3 }, { transform: 'translateY(0) rotate(0)', opacity: 1 }], 950, 120 + index * 110)
  })
  document.querySelectorAll<HTMLElement>('.hero-copy > .eyebrow, .hero-description, .hero-actions, .prototype-note').forEach((element, index) => enter(element, 100 + index * 90))
  return () => {
    disposed = true
    lifecycle.abort()
    if (scrollFrame) cancelAnimationFrame(scrollFrame)
    observers.forEach(observer => observer.disconnect())
    animations.forEach(animation => animation.cancel())
    clearTransforms()
    delete root.dataset.motion
    delete root.dataset.inputMode
    delete root.dataset.pageHidden
  }
}
