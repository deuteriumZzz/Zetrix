/// <reference types="vite/client" />
import { initializeGlobe } from './globe'
import { initializeWorkspace } from './workspace'
import { downloadJson } from './download'
import { initializeMotion } from './motion'

const disposers: Array<() => void> = []
const lifecycle = new AbortController()
const options = { signal: lifecycle.signal }
const canvas = document.getElementById('planet') as HTMLCanvasElement
disposers.push(initializeGlobe(canvas), initializeWorkspace(), initializeMotion())

const navigation = document.getElementById('navigation')!
const menu = document.querySelector<HTMLButtonElement>('.menu-toggle')!
function closeMenu(returnFocus = false) {
  menu.setAttribute('aria-expanded', 'false')
  menu.setAttribute('aria-label', 'Открыть меню')
  navigation.dataset.open = 'false'
  if (returnFocus) menu.focus()
}
menu.addEventListener('click', () => {
  const open = menu.getAttribute('aria-expanded') !== 'true'
  menu.setAttribute('aria-expanded', String(open))
  menu.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню')
  navigation.dataset.open = String(open)
}, options)
navigation.addEventListener('click', event => { if ((event.target as HTMLElement).closest('a')) closeMenu() }, options)
document.addEventListener('keydown', event => { if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') closeMenu(true) }, options)
document.addEventListener('click', event => { if (!(event.target as HTMLElement).closest('.site-header')) closeMenu() }, options)

const dialog = document.getElementById('brief-dialog') as HTMLDialogElement
let opener: HTMLElement | null = null
document.querySelectorAll<HTMLButtonElement>('[data-open-brief]').forEach(button => {
  button.addEventListener('click', () => {
    closeMenu()
    opener = button
    document.getElementById('brief-status')!.textContent = ''
    dialog.showModal()
    document.body.classList.add('modal-open')
  }, options)
})
dialog.querySelector('.dialog-close')!.addEventListener('click', () => dialog.close(), options)
dialog.addEventListener('close', () => { document.body.classList.remove('modal-open'); opener?.focus() }, options)
dialog.addEventListener('click', event => {
  if (event.target !== dialog) return
  const rect = dialog.getBoundingClientRect()
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close()
}, options)
const brief = document.getElementById('brief-form') as HTMLFormElement
brief.addEventListener('submit', event => {
  event.preventDefault()
  const status = document.getElementById('brief-status')!
  const data = new FormData(brief)
  const regions = String(data.get('regions') ?? '').trim()
  const question = String(data.get('question') ?? '').trim()
  if (!brief.reportValidity() || !regions || question.length < 20) {
    status.textContent = 'Укажите регионы и опишите задачу минимум в 20 символах.'
    return
  }
  try {
    downloadJson('zetrix-pilot-brief.json', { product: 'Zetrix', document: 'Бриф пилотного проекта', createdAt: new Date().toISOString(), sector: data.get('sector'), regions, question, status: 'Черновик для обсуждения. Заявка не отправлена.' })
    status.textContent = 'Бриф подготовлен к скачиванию. Заявка никуда не отправлена.'
  } catch { status.textContent = 'Не удалось скачать бриф. Попробуйте ещё раз.' }
}, options)

if (import.meta.hot) import.meta.hot.dispose(() => {
  lifecycle.abort()
  disposers.forEach(dispose => dispose())
  document.body.classList.remove('modal-open')
})
