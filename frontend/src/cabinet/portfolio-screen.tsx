import { useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError, orgPath } from './api'
import { canWrite, dateLabel, formatMoney } from './domain'
import type { Organization } from './types'
import { Empty, ErrorNotice, Field, Heading, Loading, RefreshError, useResource } from './ui'

export type PortfolioLine = { id?: string; supplier: string; country_code: string; category: string; monthly_cost: string; currency: 'USD' }
export type PortfolioRevision = { id: string; created_at: string; project_id: string; number?: number; lines: PortfolioLine[]; monthly_total: string; currency: 'USD' }
const blankLine = (): PortfolioLine => ({ supplier: '', country_code: '', category: '', monthly_cost: '', currency: 'USD' })
const csvHeader = 'supplier,country_code,category,monthly_cost,currency'
const maxBytes = 2 * 1024 * 1024

/** Draft display only; authoritative validation and totals belong to the server. */
export function portfolioTotal(lines: Pick<PortfolioLine, 'monthly_cost'>[]): string | null {
  if (lines.some(line => !/^\d{1,10}(\.\d{1,2})?$/.test(line.monthly_cost))) return null
  const cents = lines.reduce((sum, line) => {
    const [whole, fraction = ''] = line.monthly_cost.split('.')
    return sum + Number(whole) * 100 + Number(fraction.padEnd(2, '0'))
  }, 0)
  return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, '0')}`
}
function LineTable({ lines }: { lines: PortfolioLine[] }) {
  return <div className="data-table-scroll" tabIndex={0} role="region" aria-label="Строки портфеля"><table className="data-table"><thead><tr><th scope="col">Поставщик</th><th scope="col">Страна</th><th scope="col">Категория</th><th scope="col">Затраты / месяц</th></tr></thead><tbody>{lines.map((line, index) => <tr key={line.id || index}><td>{line.supplier}</td><td>{line.country_code}</td><td>{line.category}</td><td className="numeric">{formatMoney(line.monthly_cost)}</td></tr>)}</tbody></table></div>
}
function CSVErrors({ error }: { error: unknown }) {
  const rows = error instanceof ApiError && error.fields && typeof error.fields === 'object' && 'rows' in error.fields ? error.fields.rows : null
  if (!Array.isArray(rows)) return <ErrorNotice error={error}/>
  return <div className="error-notice" role="alert"><strong>CSV не принят. Исправьте строки и проверьте снова.</strong><ul>{rows.map((row, index) => <li key={index}>Строка {String(row.row)}: {Object.entries(row.errors || {}).map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(', ') : String(messages)}`).join(' · ')}</li>)}</ul></div>
}
function CSVImport({ path, saved }: { path: string; saved: (version: PortfolioRevision) => void }) {
  const [csv, setCSV] = useState(''), [preview, setPreview] = useState<PortfolioRevision>(), [error, setError] = useState<unknown>(), [pending, setPending] = useState(false)
  const fileGeneration = useRef(0)
  function changeCSV(value: string) { fileGeneration.current += 1; setCSV(value); setPreview(undefined); setError(undefined) }
  async function readFile(file?: File) {
    const generation = ++fileGeneration.current
    setPreview(undefined); setError(undefined)
    if (!file) return
    if (file.size > maxBytes) { setError(new Error('Размер CSV не должен превышать 2 МиБ.')); return }
    try { const value = await file.text(); if (generation === fileGeneration.current) setCSV(value) } catch { if (generation === fileGeneration.current) setError(new Error('Не удалось прочитать файл. Вставьте CSV в текстовое поле.')) }
  }
  async function inspect(event: FormEvent) {
    event.preventDefault(); setError(undefined); setPreview(undefined)
    if (new TextEncoder().encode(csv).byteLength > maxBytes) { setError(new Error('Размер CSV не должен превышать 2 МиБ.')); return }
    setPending(true)
    try { setPreview(await api.post<PortfolioRevision>(`${path}preview/`, { csv })) } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  async function confirm() {
    if (!preview || pending) return
    setPending(true); setError(undefined)
    try { const version = await api.post<PortfolioRevision>(`${path}imports/${preview.id}/confirm/`, {}); setPreview(undefined); setCSV(''); saved(version) } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  return <section className="panel data-editor"><h2>Импорт из CSV</h2><p className="muted">До 1 000 строк и 2 МиБ. Сначала проверка и предпросмотр, затем создание новой версии.</p><form onSubmit={inspect}><fieldset disabled={pending} className="data-fieldset"><Field label="CSV-файл" hint="Файл читается в браузере, содержимое отправляется в ваш проект только при проверке."><input type="file" accept=".csv,text/csv" onChange={event => void readFile(event.target.files?.[0])}/></Field><Field label="Содержимое CSV" hint={`Первая строка: ${csvHeader}. Денежные значения — с точкой, валюта — USD.`}><textarea required value={csv} onChange={event => changeCSV(event.target.value)} rows={5} placeholder={csvHeader} spellCheck={false}/></Field><button className="secondary" disabled={!csv.trim()}>{pending ? 'Обработка…' : 'Проверить CSV'}</button></fieldset></form><CSVErrors error={error}/>{preview && <div className="csv-preview"><div className="section-title"><h3>Предпросмотр · {preview.lines.length} строк</h3><span className="pill">{formatMoney(preview.monthly_total)}</span></div><LineTable lines={preview.lines}/><p className="muted">Проверьте поставщиков, страны и суммы. Подтверждение сохранит неизменяемую версию.</p><button className="primary" onClick={confirm} disabled={pending}>{pending ? 'Сохранение…' : 'Подтвердить импорт'}</button></div>}</section>
}
function ManualPortfolio({ path, saved }: { path: string; saved: (version: PortfolioRevision) => void }) {
  const [lines, setLines] = useState<PortfolioLine[]>([blankLine()]), [pending, setPending] = useState(false), [error, setError] = useState<unknown>()
  const total = portfolioTotal(lines)
  function change(index: number, field: keyof PortfolioLine, value: string) { setLines(current => current.map((line, position) => position === index ? { ...line, [field]: value } : line)) }
  async function submit(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(undefined)
    try { const version = await api.post<PortfolioRevision>(path, { lines }); setLines([blankLine()]); saved(version) } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  return <form className="panel data-editor" onSubmit={submit}><h2>Новая версия вручную</h2><p className="muted">Каждая версия содержит полный портфель. Сохранённые версии остаются в истории.</p><fieldset disabled={pending} className="data-fieldset"><div className="portfolio-draft">{lines.map((line, index) => <div className="portfolio-draft-row" key={index}><span className="draft-number">{String(index + 1).padStart(2, '0')}</span><Field label={`Поставщик ${index + 1}`}><input required maxLength={160} value={line.supplier} onChange={event => change(index, 'supplier', event.target.value)}/></Field><Field label={`Страна ${index + 1}`} hint="Код: US, DE…"><input required maxLength={2} pattern="[A-Z]{2}" value={line.country_code} onChange={event => change(index, 'country_code', event.target.value.toUpperCase())}/></Field><Field label={`Категория ${index + 1}`}><input required maxLength={120} value={line.category} onChange={event => change(index, 'category', event.target.value)}/></Field><Field label={`Затраты ${index + 1}`} hint="USD / месяц"><input required inputMode="decimal" pattern="[0-9]{1,10}(\.[0-9]{1,2})?" value={line.monthly_cost} onChange={event => change(index, 'monthly_cost', event.target.value)}/></Field><button type="button" className="secondary compact" aria-label={`Удалить строку ${index + 1}`} disabled={lines.length === 1} onClick={() => setLines(current => current.filter((_, position) => position !== index))}>×</button></div>)}</div><div className="data-actions"><button type="button" className="secondary" disabled={lines.length >= 1000} onClick={() => setLines(current => [...current, blankLine()])}>Добавить строку</button><span className="muted">Предварительная сумма: {total === null ? '—' : formatMoney(total)}</span></div><ErrorNotice error={error}/><button className="primary">{pending ? 'Сохранение…' : 'Сохранить версию'}</button></fieldset></form>
}
export function PortfolioPage({ org }: { org: Organization }) {
  const { projectId = '' } = useParams(), path = `${orgPath(org.id)}projects/${encodeURIComponent(projectId)}/portfolio/`
  const [refresh, setRefresh] = useState(0), [notice, setNotice] = useState(''), versions = useResource<PortfolioRevision[]>(path, true, refresh)
  function saved(version: PortfolioRevision) { setNotice(`Версия ${version.number} сохранена.`); setRefresh(current => current + 1) }
  return <><Link className="back-link" to={`/org/${org.id}/projects/${projectId}`}>← К проекту</Link><Heading eyebrow="PORTFOLIO / USD" title="Данные ваших закупок">Поставщики, страны и ежемесячные затраты. Выберите сохранённую версию в редакторе сценария.</Heading>{notice && <p className="data-notice" role="status">{notice}</p>}<div className="section-title"><h2>Версии портфеля</h2><span className="pill">{versions.data?.length ?? '—'} сохранено</span></div>{versions.loading ? <Loading/> : versions.error ? <RefreshError error={versions.error} retry={() => setRefresh(current => current + 1)}/> : versions.data?.length ? <div className="portfolio-versions">{versions.data.map((version, index) => <details className="panel portfolio-version" key={version.id} open={index === 0}><summary><span>Версия {version.number}<small>{dateLabel(version.created_at)} · {version.lines.length} строк</small></span><strong>{formatMoney(version.monthly_total)}</strong></summary><LineTable lines={version.lines}/></details>)}</div> : <Empty title="Портфель пока не создан">Добавьте затраты вручную или импортируйте CSV.</Empty>}{canWrite(org.role) && <div className="data-editors"><ManualPortfolio key={`${path}manual`} path={path} saved={saved}/><CSVImport key={`${path}csv`} path={path} saved={saved}/></div>}</>
}
