import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, orgPath } from './api'
import { canWrite, dateLabel, formatMoney, initialInputs, kindNames } from './domain'
import type { Inputs, Organization, Revision, Run, Scenario } from './types'
import type { EvidenceEvent, PortfolioRevision } from './data'
import { ErrorNotice, Field, Heading, Loading, RefreshError, useResource } from './ui'
export type ContextSelection = { portfolioRevisionId: string; affectedLineIds: string[]; evidenceRevisionId: string }
export const emptyContextSelection: ContextSelection = { portfolioRevisionId: '', affectedLineIds: [], evidenceRevisionId: '' }
export function contextPayload(selection: ContextSelection) {
  if (!selection.portfolioRevisionId) return selection.evidenceRevisionId ? { evidence_revision_id: selection.evidenceRevisionId } : {}
  if (!selection.affectedLineIds.length) throw new Error('Выберите хотя бы одну затронутую строку портфеля.')
  return { portfolio_revision_id: selection.portfolioRevisionId, affected_line_ids: selection.affectedLineIds, ...(selection.evidenceRevisionId ? { evidence_revision_id: selection.evidenceRevisionId } : {}) }
}
export function selectionFromRevision(revision?: Revision): ContextSelection {
  const context = (revision as (Revision & { context?: { portfolio_revision_id?: unknown; affected_line_ids?: unknown; evidence?: { revision_id?: unknown } } }) | undefined)?.context
  return { portfolioRevisionId: typeof context?.portfolio_revision_id === 'string' ? context.portfolio_revision_id : '', affectedLineIds: Array.isArray(context?.affected_line_ids) ? context.affected_line_ids.filter((id): id is string => typeof id === 'string') : [], evidenceRevisionId: typeof context?.evidence?.revision_id === 'string' ? context.evidence.revision_id : '' }
}
export function ScenarioContextFields({ org, projectId, selection, onChange, onMonthlyCost, disabled = false }: { org: Organization; projectId: string; selection: ContextSelection; onChange: (selection: ContextSelection) => void; onMonthlyCost: (cost: string) => void; disabled?: boolean }) {
  const [refresh, setRefresh] = useState(0)
  const portfolios = useResource<PortfolioRevision[]>(`${orgPath(org.id)}projects/${encodeURIComponent(projectId)}/portfolio/`, true, refresh)
  const events = useResource<EvidenceEvent[]>('evidence/events/', true, refresh)
  const portfolio = portfolios.data?.find(item => item.id === selection.portfolioRevisionId)
  const approved = events.data?.map(item => item.published_revision).filter((item): item is NonNullable<typeof item> => Boolean(item && item.publication_status === 'current')) || []
  function choosePortfolio(id: string) {
    const next = portfolios.data?.find(item => item.id === id)
    onChange({ ...selection, portfolioRevisionId: id, affectedLineIds: next?.lines.map(line => line.id).filter((line): line is string => Boolean(line)) || [] })
    if (next) onMonthlyCost(next.monthly_total)
  }
  function toggleLine(id: string) {
    onChange({ ...selection, affectedLineIds: selection.affectedLineIds.includes(id) ? selection.affectedLineIds.filter(item => item !== id) : [...selection.affectedLineIds, id] })
  }
  return <section className="scenario-context"><div className="section-title"><h3>Данные и основания</h3><span className="eyebrow">СНИМОК НА МОМЕНТ СОХРАНЕНИЯ</span></div><div className="input-grid"><Field label="Версия портфеля"><select value={selection.portfolioRevisionId} disabled={disabled || portfolios.loading || !!portfolios.error} onChange={event => choosePortfolio(event.target.value)}><option value="">Без портфеля · ручная сумма</option>{portfolios.data?.map(item => <option key={item.id} value={item.id}>Версия {item.number} · {formatMoney(item.monthly_total)}</option>)}</select></Field><Field label="Подтверждённое событие"><select value={selection.evidenceRevisionId} disabled={disabled || events.loading || !!events.error} onChange={event => onChange({ ...selection, evidenceRevisionId: event.target.value })}><option value="">Без события</option>{approved.map(item => <option key={item.revision_id} value={item.revision_id}>{item.title} · версия {item.number}</option>)}{selection.evidenceRevisionId && !approved.some(item => item.revision_id === selection.evidenceRevisionId) && <option value={selection.evidenceRevisionId} disabled>Прежняя публикация недоступна — выберите другую</option>}</select></Field></div>{portfolios.error ? <RefreshError error={portfolios.error} retry={() => setRefresh(value => value + 1)}/> : null}{events.error ? <RefreshError error={events.error} retry={() => setRefresh(value => value + 1)}/> : null}<div className="data-actions"><Link className="text-link" to={`/org/${org.id}/projects/${projectId}/portfolio`}>Открыть портфель закупок ↗</Link><Link className="text-link" to={`/org/${org.id}/events`}>Открыть реестр событий ↗</Link></div>{portfolio && <fieldset className="source-choices" disabled={disabled}><legend>Затронутые строки · выберите минимум одну</legend>{portfolio.lines.map(line => <label className="source-choice" key={line.id}><input type="checkbox" checked={Boolean(line.id && selection.affectedLineIds.includes(line.id))} onChange={() => line.id && toggleLine(line.id)}/><span>{line.supplier} · {line.country_code} · {line.category}<small>{formatMoney(line.monthly_cost)} / месяц</small></span></label>)}</fieldset>}</section>
}
export function InputFields({ inputs, onChange, disabled = false, monthlyCostLocked = false }: { inputs: Inputs; onChange: (inputs: Inputs) => void; disabled?: boolean; monthlyCostLocked?: boolean }) {
  const change = (field: keyof Inputs, value: string | number) => onChange({ ...inputs, [field]: value })
  return <fieldset className="input-grid" disabled={disabled}><legend className="sr-only">Параметры сценария</legend><Field label="Тип воздействия"><select value={inputs.kind} onChange={event => change('kind', event.target.value)}>{Object.entries(kindNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="Горизонт, месяцев"><select value={inputs.months} onChange={event => change('months', Number(event.target.value))}>{[1, 3, 6, 12].map(month => <option key={month} value={month}>{month}</option>)}</select></Field><Field label="Месячные затраты, USD" hint={monthlyCostLocked ? 'Сумма выбранной версии портфеля.' : 'От 1 до 1 000 000 000 USD'}><input type="number" min="1" max="1000000000" step="0.01" required disabled={monthlyCostLocked} value={inputs.monthly_cost} onChange={event => change('monthly_cost', event.target.value)}/></Field><Field label="Доля затронутых затрат, %"><input type="number" min="0" max="100" step="0.01" required value={inputs.exposure} onChange={event => change('exposure', event.target.value)}/></Field><Field label="Удорожание затронутой части, %"><input type="number" min="0" max="100" step="0.01" required value={inputs.shock} onChange={event => change('shock', event.target.value)}/></Field><div className="formula-note"><span>МОДЕЛЬ ПРЯМОГО ВОЗДЕЙСТВИЯ</span><p>Затраты × доля × удорожание × период</p><small>Все типы используют одну формулу.</small></div></fieldset>
}
export function ScenarioPage({ org }: { org: Organization }) {
  const { projectId = '', scenarioId = '' } = useParams(), path = `${orgPath(org.id)}projects/${projectId}/scenarios/${scenarioId}/`
  const [refresh, setRefresh] = useState(0), state = useResource<Scenario>(path, false, refresh), history = useResource<Revision[]>(`${path}revisions/`, true, refresh)
  const [inputs, setInputs] = useState<Inputs>(initialInputs), [selection, setSelection] = useState<ContextSelection>(emptyContextSelection), [pending, setPending] = useState(false), [running, setRunning] = useState<string>(), [error, setError] = useState<unknown>(), [notice, setNotice] = useState('')
  const navigate = useNavigate(), attempt = useRef<{ revision: string; key: string }>(), mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  useEffect(() => { if (state.data?.revisions?.[0]) { setInputs(state.data.revisions[0].inputs); setSelection(selectionFromRevision(state.data.revisions[0])) } }, [state.data])
  async function save(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(undefined); setNotice('')
    try { const revision = await api.post<Revision>(`${path}revisions/`, { inputs, ...contextPayload(selection) }); if (mounted.current) { setNotice(`Версия ${revision.number} сохранена. Предыдущие результаты остаются неизменными.`); setRefresh(x => x + 1) } } catch (failure) { if (mounted.current) setError(failure) } finally { if (mounted.current) setPending(false) }
  }
  async function run(revision: Revision) {
    setRunning(revision.id); setError(undefined)
    if (attempt.current?.revision !== revision.id) attempt.current = { revision: revision.id, key: crypto.randomUUID() }
    try { const result = await api.post<Run>(`${orgPath(org.id)}runs/`, { revision_id: revision.id }, { 'Idempotency-Key': attempt.current.key }); if (mounted.current) { attempt.current = undefined; navigate(`/org/${org.id}/runs/${result.id}`) } } catch (failure) { if (mounted.current) setError(failure) } finally { if (mounted.current) setRunning(undefined) }
  }
  if (state.loading) return <Loading/>
  if (state.error || !state.data) return <RefreshError error={state.error} retry={() => setRefresh(x => x + 1)}/>
  const latest = state.data.revisions?.[0]
  return <><Link className="back-link" to={`/org/${org.id}/projects/${projectId}`}>← К проекту</Link><Heading eyebrow={`SCENARIO / REVISION ${latest?.number ?? '—'}`} title={state.data.title}>Каждая сохранённая версия фиксирует вводные. Расчёт всегда привязан к выбранной версии.</Heading><ErrorNotice error={error}/>{notice && <div className="success-notice" role="status">{notice}</div>}<form className="panel editor" onSubmit={save}><div className="section-title"><h2>{canWrite(org.role) ? 'Вводные новой версии' : 'Сохранённые вводные'}</h2><span className="pill">USD</span></div><ScenarioContextFields org={org} projectId={projectId} selection={selection} onChange={setSelection} onMonthlyCost={cost => setInputs(current => ({ ...current, monthly_cost: cost }))} disabled={!canWrite(org.role) || pending || !!running}/><InputFields inputs={inputs} onChange={setInputs} disabled={!canWrite(org.role) || pending || !!running} monthlyCostLocked={!!selection.portfolioRevisionId}/>{canWrite(org.role) && <div className="action-row"><button className="secondary" disabled={pending || !!running}>{pending ? 'Сохранение…' : 'Сохранить новую версию'}</button><p>Запуск ниже использует сохранённые вводные, включая прежнюю версию.</p></div>}</form><div className="section-title"><h2>История версий</h2><span className="eyebrow">IMMUTABLE INPUTS</span></div>{history.loading ? <Loading/> : history.error ? <RefreshError error={history.error} retry={() => setRefresh(x => x + 1)}/> : <div className="revision-list">{history.data?.map(revision => <article className="panel revision-card" key={revision.id}><div><span className="pill">Версия {revision.number}</span><h3>{kindNames[revision.inputs.kind]}</h3><p>{formatMoney(revision.inputs.monthly_cost)} / месяц</p><small>{revision.inputs.exposure}% затрат · +{revision.inputs.shock}% · {revision.inputs.months} мес.</small><time dateTime={revision.created_at}>{dateLabel(revision.created_at)}</time></div>{canWrite(org.role) && <button className="primary" disabled={!!running || pending} onClick={() => run(revision)}>{running === revision.id ? 'Расчёт…' : 'Рассчитать ↗'}</button>}</article>)}</div>}</>
}
