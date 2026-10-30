import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { App, Login } from './App'
import { ProjectPage, Projects } from './projects'
import { ScenarioPage } from './scenario'
import { api, ApiError } from './api'
import type { Organization } from './types'
import { initialInputs } from './domain'
const org = { id: 'o1', name: 'Acme', role: 'analyst', created_at: '2026-10-16T00:00:00Z' } as Organization
const revision = { id: 'r1', number: 1, scenario_id: 's1', inputs: initialInputs, created_at: org.created_at }
const portfolio = { id: 'portfolio-1', number: 2, created_at: org.created_at, monthly_total: '300.00', lines: [
  { id: 'line-1', supplier: 'Acme', country_code: 'US', category: 'Parts', monthly_cost: '100.00', currency: 'USD' },
  { id: 'line-2', supplier: 'Beta', country_code: 'DE', category: 'Parts', monthly_cost: '200.00', currency: 'USD' },
] }
const published = { id: 'event-1', published_revision: { id: 'evidence-1', revision_id: 'evidence-1', number: 1, title: 'Approved event', summary: 'Verified', country_codes: ['US'], effective_at: org.created_at, sources: [], provenance: 'Manual review', event_kind: 'trade', publication_status: 'current' } }
const draft = { id: 'event-2', latest_revision: { id: 'evidence-2', revision_id: 'evidence-2', number: 1, title: 'Draft event', publication_status: 'draft' }, published_revision: null }
function mockLists() {
  return vi.spyOn(api, 'all').mockImplementation(async path => {
    if (path.endsWith('portfolio/')) return [portfolio]
    if (path === 'evidence/events/') return [published, draft]
    if (path.endsWith('scenarios/')) return []
    if (path.endsWith('revisions/')) return [revision]
    return []
  })
}
afterEach(() => { cleanup(); vi.restoreAllMocks() })
describe('cabinet workflows', () => {
  it('logs in and clears password immediately on submission', async () => {
    const login = vi.spyOn(api, 'login').mockResolvedValue({ id: 1, username: 'ana' }), done = vi.fn()
    render(<Login onLogin={done}/>)
    fireEvent.change(screen.getByLabelText('Имя пользователя'), { target: { value: 'ana' } })
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'secret' } })
    fireEvent.click(screen.getByRole('button', { name: /Войти в кабинет/ }))
    expect(screen.getByLabelText('Пароль')).toHaveValue('')
    await waitFor(() => expect(done).toHaveBeenCalledWith({ id: 1, username: 'ana' }))
    expect(login).toHaveBeenCalledWith('ana', 'secret')
  })
  it('shows a readable login error without claiming success', async () => {
    vi.spyOn(api, 'login').mockRejectedValue(new ApiError(403, 'authentication_failed', 'Invalid'))
    render(<Login onLogin={vi.fn()}/>)
    fireEvent.submit(screen.getByRole('button', { name: /Войти в кабинет/ }).closest('form')!)
    expect(await screen.findByRole('alert')).toHaveTextContent('Неверный логин или пароль')
  })
  it('hides mutation actions for a viewer', async () => {
    vi.spyOn(api, 'all').mockResolvedValue([])
    render(<MemoryRouter><Projects org={{ ...org, role: 'viewer' }}/></MemoryRouter>)
    await screen.findByText('Начните с первого проекта')
    expect(screen.queryByRole('button', { name: /Создать проект/ })).not.toBeInTheDocument()
  })
  it('creates a project through the API and opens its route', async () => {
    vi.spyOn(api, 'all').mockResolvedValue([])
    const post = vi.spyOn(api, 'post').mockResolvedValue({ id: 'p1' })
    render(<MemoryRouter><Routes><Route path="/" element={<Projects org={org}/>}/><Route path="/org/o1/projects/p1" element={<h1>Created project</h1>}/></Routes></MemoryRouter>)
    fireEvent.change(screen.getByLabelText('Название нового проекта'), { target: { value: 'Imports' } })
    fireEvent.click(screen.getByRole('button', { name: /Создать проект/ }))
    await screen.findByText('Created project')
    expect(post).toHaveBeenCalledWith('organizations/o1/projects/', { title: 'Imports', currency: 'USD' })
  })
  it('opens an existing project and its saved scenario', async () => {
    const project = { id: 'p1', title: 'Imports', created_at: org.created_at }
    const scenario = { id: 's1', title: 'Supply shock', created_at: org.created_at }
    vi.spyOn(api, 'request').mockResolvedValue(project)
    vi.spyOn(api, 'all').mockImplementation(async path => path === 'organizations/o1/projects/' ? [project] : path.endsWith('scenarios/') ? [scenario] : [])
    render(<MemoryRouter initialEntries={['/org/o1']}><Routes><Route path="/org/:orgId" element={<Projects org={org}/>}/><Route path="/org/:orgId/projects/:projectId" element={<ProjectPage org={org}/>}/><Route path="/org/o1/projects/p1/scenarios/s1" element={<h1>Saved scenario</h1>}/></Routes></MemoryRouter>)
    fireEvent.click(await screen.findByRole('link', { name: /Imports/ }))
    expect(await screen.findByRole('heading', { name: 'Imports' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: /Supply shock/ }))
    expect(await screen.findByRole('heading', { name: 'Saved scenario' })).toBeInTheDocument()
  })
  it('retries a failed project load without losing the route', async () => {
    const request = vi.spyOn(api, 'request').mockRejectedValueOnce(new ApiError(0, 'network_error', 'Нет связи')).mockResolvedValueOnce({ id: 'p1', title: 'Imports' })
    vi.spyOn(api, 'all').mockResolvedValue([])
    render(<MemoryRouter initialEntries={['/org/o1/projects/p1']}><Routes><Route path="/org/:orgId/projects/:projectId" element={<ProjectPage org={org}/>}/></Routes></MemoryRouter>)
    expect(await screen.findByRole('alert')).toHaveTextContent('Нет связи')
    fireEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }))
    expect(await screen.findByRole('heading', { name: 'Imports' })).toBeInTheDocument()
    expect(request).toHaveBeenCalledTimes(2)
  })
  it('exposes portfolio and evidence routes in the cabinet', async () => {
    vi.spyOn(api, 'request').mockImplementation(async path => {
      if (path === 'auth/me/') return { id: 1, username: 'ana' }
      if (path === 'organizations/o1/') return org
      return { id: 'p1', title: 'Imports' }
    })
    mockLists()
    render(<MemoryRouter initialEntries={['/org/o1/projects/p1/portfolio']}><App/></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: 'Данные ваших закупок' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: /События/ }))
    expect(await screen.findByRole('heading', { name: 'События и основания' })).toBeInTheDocument()
  })
  it('links a project to its portfolio', async () => {
    vi.spyOn(api, 'request').mockResolvedValue({ id: 'p1', title: 'Imports' })
    mockLists()
    render(<MemoryRouter initialEntries={['/org/o1/projects/p1']}><Routes><Route path="/org/:orgId/projects/:projectId" element={<ProjectPage org={org}/>}/></Routes></MemoryRouter>)
    expect(await screen.findByRole('link', { name: /Портфель закупок/ })).toHaveAttribute('href', '/org/o1/projects/p1/portfolio')
  })
  it('saves a scenario with a selected portfolio line and approved event', async () => {
    vi.spyOn(api, 'request').mockResolvedValue({ id: 'p1', title: 'Imports' })
    mockLists()
    const post = vi.spyOn(api, 'post').mockResolvedValue({ id: 's1' })
    render(<MemoryRouter initialEntries={['/org/o1/projects/p1']}><Routes><Route path="/org/:orgId/projects/:projectId" element={<ProjectPage org={org}/>}/><Route path="/org/o1/projects/p1/scenarios/s1" element={<h1>Created scenario</h1>}/></Routes></MemoryRouter>)
    await screen.findByRole('option', { name: /Версия 2/ })
    fireEvent.change(screen.getByLabelText('Название сценария'), { target: { value: 'Supply shock' } })
    fireEvent.change(screen.getByLabelText('Версия портфеля'), { target: { value: portfolio.id } })
    fireEvent.click(screen.getByRole('checkbox', { name: /Beta/ }))
    fireEvent.change(screen.getByLabelText('Подтверждённое событие'), { target: { value: 'evidence-1' } })
    expect(screen.queryByRole('option', { name: /Draft event/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Сохранить сценарий/ }))
    await screen.findByText('Created scenario')
    expect(post).toHaveBeenCalledWith('organizations/o1/projects/p1/scenarios/', { title: 'Supply shock', inputs: { ...initialInputs, monthly_cost: '300.00' }, portfolio_revision_id: 'portfolio-1', affected_line_ids: ['line-1'], evidence_revision_id: 'evidence-1' })
  })
  it('requires at least one affected portfolio line', async () => {
    vi.spyOn(api, 'request').mockResolvedValue({ id: 'p1', title: 'Imports' })
    mockLists()
    const post = vi.spyOn(api, 'post')
    render(<MemoryRouter initialEntries={['/org/o1/projects/p1']}><Routes><Route path="/org/:orgId/projects/:projectId" element={<ProjectPage org={org}/>}/></Routes></MemoryRouter>)
    await screen.findByRole('option', { name: /Версия 2/ })
    fireEvent.change(screen.getByLabelText('Название сценария'), { target: { value: 'No affected lines' } })
    fireEvent.change(screen.getByLabelText('Версия портфеля'), { target: { value: portfolio.id } })
    fireEvent.click(screen.getByRole('checkbox', { name: /Acme/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /Beta/ }))
    fireEvent.click(screen.getByRole('button', { name: /Сохранить сценарий/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Выберите хотя бы одну затронутую строку')
    expect(post).not.toHaveBeenCalled()
  })
  it('retains saved context when creating a new scenario revision', async () => {
    const withContext = { ...revision, context: { portfolio_revision_id: portfolio.id, affected_line_ids: ['line-1'], evidence: { revision_id: 'evidence-1', title: 'Approved event' } }, inputs: { ...initialInputs, monthly_cost: '300.00' } }
    vi.spyOn(api, 'request').mockResolvedValue({ id: 's1', title: 'Scenario', revisions: [withContext] })
    mockLists().mockImplementation(async path => path.endsWith('revisions/') ? [withContext] : path.endsWith('portfolio/') ? [portfolio] : path === 'evidence/events/' ? [published] : [])
    const post = vi.spyOn(api, 'post').mockResolvedValue({ id: 'r2', number: 2 })
    render(<MemoryRouter initialEntries={['/org/o1/projects/p1/scenarios/s1']}><Routes><Route path="/org/:orgId/projects/:projectId/scenarios/:scenarioId" element={<ScenarioPage org={org}/>}/></Routes></MemoryRouter>)
    await screen.findByRole('option', { name: /Версия 2/ })
    await waitFor(() => expect(screen.getByLabelText('Версия портфеля')).toHaveValue(portfolio.id))
    expect(screen.getByLabelText('Подтверждённое событие')).toHaveValue('evidence-1')
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить новую версию' }))
    await waitFor(() => expect(post).toHaveBeenCalledWith('organizations/o1/projects/p1/scenarios/s1/revisions/', { inputs: withContext.inputs, portfolio_revision_id: portfolio.id, affected_line_ids: ['line-1'], evidence_revision_id: 'evidence-1' }))
  })
  it('reuses the same idempotency key after a failed run request', async () => {
    vi.spyOn(api, 'request').mockResolvedValue({ id: 's1', title: 'Scenario', revisions: [revision] })
    vi.spyOn(api, 'all').mockImplementation(async path => path.endsWith('revisions/') ? [revision] : [])
    const post = vi.spyOn(api, 'post').mockRejectedValueOnce(new ApiError(0, 'network_error', 'Нет связи')).mockResolvedValueOnce({ id: 'run1' })
    render(<MemoryRouter initialEntries={['/org/o1/projects/p1/scenarios/s1']}><Routes><Route path="/org/:orgId/projects/:projectId/scenarios/:scenarioId" element={<ScenarioPage org={org}/>}/><Route path="/org/o1/runs/run1" element={<h1>Saved result</h1>}/></Routes></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: 'Рассчитать ↗' }))
    await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button', { name: 'Рассчитать ↗' }))
    await screen.findByText('Saved result')
    expect(post.mock.calls[0][2]).toEqual(post.mock.calls[1][2])
    expect(post.mock.calls[0][1]).toEqual({ revision_id: 'r1' })
  })
})
