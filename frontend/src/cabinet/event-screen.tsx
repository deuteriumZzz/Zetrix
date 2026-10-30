import { useState, type FormEvent } from 'react'
import { api } from './api'
import { dateLabel } from './domain'
import type { User } from './types'
import { Empty, ErrorNotice, Field, Heading, Loading, RefreshError, useResource } from './ui'

export type EvidenceSource = { id: string; publisher: string; url: string; allowed_use: string }
export type EventRevision = { id: string; revision_id: string; number: number; title: string; summary: string; event_kind: string; country_codes: string[]; effective_at: string; provenance: string; sources: EvidenceSource[]; publication_status: string }
export type EvidenceEvent = { id: string; published_revision: EventRevision | null; historical_revision?: EventRevision | null; latest_revision?: EventRevision | null }
const eventKinds: Record<string, string> = { trade_restriction: 'Торговые ограничения', supply_disruption: 'Сбой поставок', energy_shock: 'Энергетический шок', other: 'Другое' }
const statuses: Record<string, string> = { current: 'Опубликовано', superseded: 'Заменено новой версией', withdrawn: 'Отозвано', draft: 'Черновик' }
function safeURL(value: string) {
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password ? url.href : null } catch { return null }
}
function SourceLink({ source }: { source: EvidenceSource }) {
  const href = safeURL(source.url)
  return <li>{href ? <a href={href} target="_blank" rel="noopener noreferrer">{source.publisher} ↗</a> : <span>{source.publisher}</span>}<small>{source.allowed_use}</small></li>
}
function localTime(value?: string) {
  if (!value) return ''
  const time = new Date(value)
  return new Date(time.getTime() - time.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
function RevisionForm({ sources, path, initial, saved }: { sources: EvidenceSource[]; path: string; initial?: EventRevision; saved: () => void }) {
  const [pending, setPending] = useState(false), [error, setError] = useState<unknown>()
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setPending(true); setError(undefined)
    const form = event.currentTarget, values = new FormData(form)
    try {
      const source_ids = values.getAll('sources').map(String)
      if (!source_ids.length) throw new Error('Выберите хотя бы один источник.')
      const data = { title: String(values.get('title')).trim(), summary: String(values.get('summary')).trim(), event_kind: String(values.get('kind')), country_codes: String(values.get('countries')).split(',').map(value => value.trim().toUpperCase()), effective_at: new Date(String(values.get('effective'))).toISOString(), provenance: String(values.get('provenance')).trim(), source_ids }
      await api.post(path, data); form.reset(); saved()
    } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  return <form className="event-form" onSubmit={submit}><fieldset className="data-fieldset" disabled={pending}><Field label="Заголовок события"><input name="title" required maxLength={200} defaultValue={initial?.title}/></Field><Field label="Краткое описание"><textarea name="summary" required maxLength={2000} rows={3} defaultValue={initial?.summary}/></Field><div className="data-form-grid"><Field label="Тип события"><select name="kind" defaultValue={initial?.event_kind || 'trade_restriction'}>{Object.entries(eventKinds).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="Коды стран" hint="Двухбуквенные коды через запятую: US, DE"><input name="countries" required maxLength={120} pattern="[A-Za-z]{2}(\s*,\s*[A-Za-z]{2})*" defaultValue={initial?.country_codes.join(', ')}/></Field><Field label="Дата и время вступления в силу" hint="В вашем локальном часовом поясе."><input name="effective" type="datetime-local" required defaultValue={localTime(initial?.effective_at)}/></Field></div><Field label="Основания и способ проверки" hint="Как проверено утверждение, кем и на основании каких материалов."><textarea name="provenance" required maxLength={1000} rows={3} defaultValue={initial?.provenance}/></Field><fieldset className="source-choices"><legend>Источники · выберите от 1 до 10</legend>{sources.length ? sources.map(source => <label className="source-choice" key={source.id}><input type="checkbox" name="sources" value={source.id} defaultChecked={initial?.sources.some(item => item.id === source.id)}/><span>{source.publisher}<small>{source.url}</small></span></label>) : <p className="muted">Сначала добавьте источник в реестр.</p>}</fieldset><ErrorNotice error={error}/><button className="primary" disabled={!sources.length}>{pending ? 'Сохранение…' : initial ? 'Сохранить новую версию' : 'Создать черновик'}</button></fieldset></form>
}
function RevisionEditor({ event, saved }: { event: EvidenceEvent; saved: () => void }) {
  const [refresh, setRefresh] = useState(0), sources = useResource<EvidenceSource[]>('evidence/sources/', true, refresh)
  return <div className="revision-editor"><h3>Новая версия события</h3><p className="muted">Изменения сохраняются в черновик. Опубликуйте версию после проверки.</p>{sources.loading ? <Loading/> : sources.error ? <RefreshError error={sources.error} retry={() => setRefresh(current => current + 1)}/> : <RevisionForm sources={sources.data || []} path={`evidence/events/${event.id}/revisions/`} initial={event.latest_revision || event.published_revision || undefined} saved={saved}/>}</div>
}
function EventCard({ event, staff, changed }: { event: EvidenceEvent; staff: boolean; changed: () => void }) {
  const revision = staff ? event.latest_revision || event.published_revision || event.historical_revision : event.published_revision || event.historical_revision
  const [pending, setPending] = useState(false), [error, setError] = useState<unknown>(), [editing, setEditing] = useState(false)
  if (!revision) return null
  async function mutate(action: string, body: unknown) {
    if (!staff || pending) return
    setPending(true); setError(undefined)
    try { await api.post(`evidence/events/${event.id}/${action}/`, body); changed() } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  function revoke(event: FormEvent<HTMLFormElement>) { event.preventDefault(); void mutate('revoke', { reason: String(new FormData(event.currentTarget).get('reason')).trim() }) }
  return <article className="panel evidence-card"><div className="section-title"><span className="eyebrow">{eventKinds[revision.event_kind] || revision.event_kind}</span><span className={`pill evidence-status status-${revision.publication_status}`}>{statuses[revision.publication_status] || revision.publication_status}</span></div><h2>{revision.title}</h2><p className="evidence-summary">{revision.summary}</p><div className="evidence-meta"><span>Версия {revision.number}</span><span>{revision.country_codes.join(' · ')}</span><time dateTime={revision.effective_at}>{dateLabel(revision.effective_at)}</time></div><details className="evidence-detail"><summary>Источники и проверка</summary><p>{revision.provenance}</p><ul className="evidence-sources">{revision.sources.map(source => <SourceLink key={source.id} source={source}/>)}</ul></details>{staff && <div className="curation-actions">{event.published_revision && event.published_revision.revision_id !== revision.revision_id && <p className="muted">Пользователям сейчас доступна опубликованная версия {event.published_revision.number}.</p>}<div className="data-actions">{event.published_revision?.revision_id !== revision.revision_id && <button className="primary" disabled={pending} onClick={() => void mutate('publish', { revision_id: revision.revision_id })}>Опубликовать версию {revision.number}</button>}<button className="secondary" disabled={pending} onClick={() => setEditing(current => !current)}>{editing ? 'Закрыть редактор' : 'Создать новую версию'}</button></div>{event.published_revision && <details className="evidence-detail"><summary>Отозвать публикацию</summary><form onSubmit={revoke}><Field label="Причина отзыва"><textarea name="reason" required maxLength={1000} rows={2} disabled={pending}/></Field><button className="secondary" disabled={pending}>Подтвердить отзыв</button></form></details>}<ErrorNotice error={error}/>{editing && <RevisionEditor event={event} saved={() => { setEditing(false); changed() }}/>}</div>}</article>
}
function SourceForm({ saved }: { saved: () => void }) {
  const [pending, setPending] = useState(false), [error, setError] = useState<unknown>(), [notice, setNotice] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget, values = new FormData(form)
    setPending(true); setError(undefined); setNotice('')
    try {
      const url = String(values.get('url')).trim()
      if (!safeURL(url)) throw new Error('Укажите HTTP(S)-адрес без логина и пароля.')
      await api.post('evidence/sources/', { publisher: String(values.get('publisher')).trim(), url, allowed_use: String(values.get('allowed_use')).trim() })
      form.reset(); setNotice('Источник добавлен в реестр.'); saved()
    } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  return <form className="event-form" onSubmit={submit}><fieldset disabled={pending} className="data-fieldset"><Field label="Издатель / организация"><input name="publisher" required maxLength={200}/></Field><Field label="Ссылка на источник"><input name="url" type="url" required maxLength={2000} placeholder="https://"/></Field><Field label="Разрешённое использование" hint="Укажите лицензию или условия цитирования. Наличие ссылки само по себе не даёт права на перепубликацию."><textarea name="allowed_use" required maxLength={1000} rows={3}/></Field><ErrorNotice error={error}/>{notice && <p role="status">{notice}</p>}<button className="secondary">{pending ? 'Сохранение…' : 'Добавить источник'}</button></fieldset></form>
}
function StaffTools({ changed }: { changed: () => void }) {
  const [refresh, setRefresh] = useState(0), [notice, setNotice] = useState(''), sources = useResource<EvidenceSource[]>('evidence/sources/', true, refresh)
  return <section className="panel data-editor"><div className="section-title"><h2>Редактор реестра</h2><span className="pill">Куратор</span></div><p className="muted">Каждое событие проходит ручную проверку. Создание черновика и публикация — отдельные действия.</p><details className="evidence-detail"><summary>Добавить источник</summary><SourceForm saved={() => setRefresh(current => current + 1)}/></details><details className="evidence-detail"><summary>Создать событие</summary>{sources.loading ? <Loading/> : sources.error ? <RefreshError error={sources.error} retry={() => setRefresh(current => current + 1)}/> : <RevisionForm sources={sources.data || []} path="evidence/events/" saved={() => { setNotice('Черновик создан. Проверьте его перед публикацией.'); changed() }}/>}</details>{notice && <p className="data-notice" role="status">{notice}</p>}</section>
}
export function EventsPage({ user }: { user: User }) {
  const [refresh, setRefresh] = useState(0), events = useResource<EvidenceEvent[]>('evidence/events/', true, refresh), staff = Boolean(user.is_staff)
  const changed = () => setRefresh(current => current + 1)
  return <><Heading eyebrow="EVIDENCE / REGISTRY" title="События и основания">Проверенные публикации с источниками, датами и историей версий. Событие помогает обосновать сценарий; величину воздействия задаёт аналитик.</Heading>{staff && <StaffTools changed={changed}/>}<div className="section-title"><h2>{staff ? 'Реестр событий' : 'Опубликованные события'}</h2><span className="pill">{events.data?.length ?? '—'} записей</span></div>{events.loading ? <Loading/> : events.error ? <RefreshError error={events.error} retry={changed}/> : events.data?.length ? <div className="evidence-list">{events.data.map(event => <EventCard key={event.id} event={event} staff={staff} changed={changed}/>)}</div> : <Empty title={staff ? 'В реестре пока нет событий' : 'Опубликованных событий пока нет'}>Новые события появятся после добавления источников и проверки куратором.</Empty>}</>
}
