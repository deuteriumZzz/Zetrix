import { useEffect, useState, type FormEvent } from 'react'
import { Link, NavLink, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { api, ApiError, orgPath } from './api'
import { roleNames } from './domain'
import { Empty, ErrorNotice, Field, Heading, Loading, RefreshError, useResource } from './ui'
import type { Organization, User } from './types'
import { Projects, ProjectPage } from './projects'
import { ScenarioPage } from './scenario'
import { History, RunPage } from './results'
import { Team } from './team'
import { EventsPage, PortfolioPage } from './data'

export function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [pending, setPending] = useState(false), [error, setError] = useState<unknown>()
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget, values = new FormData(form)
    setPending(true); setError(undefined)
    const password = String(values.get('password')); (form.elements.namedItem('password') as HTMLInputElement).value = ''
    try { onLogin(await api.login(String(values.get('username')).trim(), password)) } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  return <main className="login-page"><a className="brand" href="/">ZETRIX<span>◈</span></a><div className="login-orbit" aria-hidden="true"/><section className="login-card"><span className="eyebrow">SCENARIO INTELLIGENCE / WORKSPACE</span><h1>Следующий шаг<br/><em>начинается здесь.</em></h1><p>Войдите в рабочее пространство команды. Сценарии, допущения и решения — в одном месте.</p><form onSubmit={submit}><Field label="Имя пользователя"><input name="username" autoComplete="username" required maxLength={150} autoFocus /></Field><Field label="Пароль"><input name="password" type="password" autoComplete="current-password" required maxLength={256}/></Field><ErrorNotice error={error}/><button className="primary" disabled={pending}>{pending ? 'Вход…' : 'Войти в кабинет'}<span>↗</span></button></form><small>Закрытый пилот. Учётную запись выдаёт администратор вашей команды.</small><a className="text-link" href="/">← На главную</a></section></main>
}
export function App() {
  const [user, setUser] = useState<User | null>(), [error, setError] = useState<unknown>(), [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController(); setError(undefined)
    api.request<User>('auth/me/', { signal: controller.signal }).then(result => { if (!controller.signal.aborted) setUser(result) }).catch(failure => {
      if (controller.signal.aborted) return
      if (failure instanceof ApiError && ['not_authenticated', 'authentication_failed'].includes(failure.code)) setUser(null)
      else setError(failure)
    })
    const expired = () => setUser(null)
    document.addEventListener('zetrix:session-expired', expired)
    return () => { controller.abort(); document.removeEventListener('zetrix:session-expired', expired) }
  }, [attempt])
  if (error) return <main className="standalone"><Heading eyebrow="ZETRIX / CONNECTION" title="Не удалось открыть кабинет"/><RefreshError error={error} retry={() => setAttempt(value => value + 1)}/><a href="/">На главную</a></main>
  if (user === undefined) return <main className="standalone"><Loading label="Проверяем сессию…"/></main>
  if (!user) return <Login onLogin={setUser}/>
  return <Routes><Route path="/" element={<Organizations user={user} onLogout={() => setUser(null)}/>}/><Route path="/org/:orgId/*" element={<Workspace user={user} onLogout={() => setUser(null)}/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes>
}
export function Logout({ onLogout }: { onLogout: () => void }) {
  const [error, setError] = useState<unknown>(), [pending, setPending] = useState(false)
  return <><button className="logout" disabled={pending} onClick={async () => { setPending(true); setError(undefined); try { await api.request('auth/logout/', { method: 'POST' }); onLogout() } catch (failure) { setError(failure) } finally { setPending(false) } }}>{pending ? 'Выход…' : 'Выйти ↗'}</button><ErrorNotice error={error}/></>
}
function Organizations({ user, onLogout }: { user: User; onLogout: () => void }) {
  const navigate = useNavigate(), [refresh, setRefresh] = useState(0), state = useResource<Organization[]>('organizations/', true, refresh)
  const [error, setError] = useState<unknown>(), [pending, setPending] = useState(false)
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(undefined); setPending(true)
    try { const organization = await api.post<Organization>('organizations/', { name: String(new FormData(event.currentTarget).get('name')).trim() }); navigate(`/org/${organization.id}`) } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  return <main className="standalone org-page"><div className="topline"><a className="brand" href="/">ZETRIX<span>◈</span></a><Logout onLogout={onLogout}/></div><Heading eyebrow={`WORKSPACE / ${user.username}`} title="Ваши организации">Выберите команду, чтобы продолжить анализ, или создайте своё пространство.</Heading>{state.loading ? <Loading/> : state.error ? <RefreshError error={state.error} retry={() => setRefresh(x => x + 1)}/> : <div className="org-grid">{state.data?.map(org => <Link className="org-card panel" key={org.id} to={`/org/${org.id}`}><span className="eyebrow">ORGANIZATION</span><h2>{org.name}</h2><span>Открыть пространство ↗</span></Link>)}{!state.data?.length && <Empty title="Пока нет организаций">Создайте команду для первого проекта.</Empty>}</div>}<form className="panel inline-form" onSubmit={create}><Field label="Новая организация"><input name="name" placeholder="Название команды" required maxLength={160}/></Field><button className="primary" disabled={pending}>{pending ? 'Создание…' : 'Создать организацию'}</button><ErrorNotice error={error}/></form></main>
}
function Workspace({ user, onLogout }: { user: User; onLogout: () => void }) {
  const { orgId = '' } = useParams()
  return <WorkspaceContent key={orgId} orgId={orgId} user={user} onLogout={onLogout}/>
}
function WorkspaceContent({ orgId, user, onLogout }: { orgId: string; user: User; onLogout: () => void }) {
  const [refresh, setRefresh] = useState(0), org = useResource<Organization>(orgPath(orgId), false, refresh)
  const [paused, setPaused] = useState(false)
  if (org.loading) return <main className="standalone"><Loading/></main>
  if (org.error || !org.data) return <main className="standalone"><RefreshError error={org.error} retry={() => setRefresh(x => x + 1)}/><Link to="/">Выбрать организацию</Link></main>
  const base = `/org/${orgId}`, organization = org.data
  return <div className="cabinet" data-motion={paused ? 'paused' : 'full'}><a className="skip-link" href="#workspace-main">Перейти к содержимому</a><aside className="sidebar"><a className="brand" href="/">ZETRIX<span>◈</span></a><Link className="org-selector" to="/" aria-label="Сменить организацию"><span>{organization.name}</span><span>⌄</span></Link><span className="sidebar-caption">РАБОЧЕЕ ПРОСТРАНСТВО</span><nav aria-label="Кабинет"><NavLink to={base} end>▦ <span>Проекты</span></NavLink><NavLink to={`${base}/events`}>◇ <span>События</span></NavLink><NavLink to={`${base}/history`}>◷ <span>История расчётов</span></NavLink><NavLink to={`${base}/team`}>◎ <span>Команда</span></NavLink></nav><div className="sidebar-foot"><span className="model-tag"><i/> DIRECT COST MODEL</span><p>Прозрачные вводные.<br/>Воспроизводимый результат.</p><button className="motion-control" aria-pressed={paused} onClick={() => setPaused(value => !value)}>{paused ? '▷ Включить анимации' : 'Ⅱ Пауза анимаций'}</button></div></aside><div className="workspace-shell"><header className="workspace-top"><span><i className="status-dot"/> {roleNames[organization.role || 'viewer']}</span><div><span>{user.username}</span><Logout onLogout={onLogout}/></div></header><main id="workspace-main" className="workspace-main"><Routes><Route index element={<Projects org={organization}/>}/><Route path="projects/:projectId" element={<ProjectPage org={organization}/>}/><Route path="projects/:projectId/portfolio" element={<PortfolioPage org={organization}/>}/><Route path="projects/:projectId/scenarios/:scenarioId" element={<ScenarioPage org={organization}/>}/><Route path="events" element={<EventsPage user={user}/>}/><Route path="history" element={<History org={organization}/>}/><Route path="runs/:runId" element={<RunPage org={organization}/>}/><Route path="team" element={<Team org={organization} onMembershipChange={() => setRefresh(x => x + 1)}/>}/><Route path="*" element={<Empty title="Страница не найдена"><Link to={base}>Вернуться к проектам</Link></Empty>}/></Routes><footer className="workspace-footer"><span>ZETRIX / SCENARIO LAB</span><span>Условный расчёт · USD · Данные вашей команды</span></footer></main></div></div>
}
