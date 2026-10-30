import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { App } from './App'
import { History } from './results'
import { api, ApiError } from './api'
import type { Organization, Run } from './types'

const org: Organization = { id: 'o1', name: 'Acme', role: 'owner', created_at: '2026-10-17T00:00:00Z' }
const base = { id: 'run-1', created_at: org.created_at, project_id: 'project-1', revision_id: 'revision-1', status: 'succeeded', inputs: { kind: 'trade', monthly_cost: '100.00', exposure: '50.00', shock: '20.00', months: 3, currency: 'USD' }, results: { baseline_total: '300.00', additional_total: '30.00', scenario_total: '330.00', additional_monthly: '10.00', exposed_monthly: '50.00', increase_percent: '10.00', currency: 'USD' }, engine_version: 'direct-cost-v1', assumptions: [] } as Run
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('workspace navigation', () => {
  it('creates an organization and opens its project workspace', async () => {
    vi.spyOn(api, 'request').mockImplementation(async path => path === 'auth/me/' ? { id: 1, username: 'ana' } : org)
    vi.spyOn(api, 'all').mockResolvedValue([])
    const post = vi.spyOn(api, 'post').mockResolvedValue(org)
    render(<MemoryRouter><App/></MemoryRouter>)
    fireEvent.change(await screen.findByLabelText('Новая организация'), { target: { value: 'Acme' } })
    fireEvent.click(screen.getByRole('button', { name: 'Создать организацию' }))
    expect(await screen.findByRole('link', { name: /События/ })).toHaveAttribute('href', '/org/o1/events')
    expect(post).toHaveBeenCalledWith('organizations/', { name: 'Acme' })
  })
  it('recovers from a temporary session check failure', async () => {
    const request = vi.spyOn(api, 'request').mockRejectedValueOnce(new ApiError(0, 'network_error', 'Нет связи')).mockResolvedValueOnce({ id: 1, username: 'ana' })
    vi.spyOn(api, 'all').mockResolvedValue([])
    render(<MemoryRouter><App/></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: 'Не удалось открыть кабинет' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }))
    expect(await screen.findByRole('heading', { name: 'Ваши организации' })).toBeInTheDocument()
    expect(request).toHaveBeenCalledTimes(2)
  })
  it('logs out from the workspace and returns to login', async () => {
    vi.spyOn(api, 'request').mockImplementation(async path => path === 'auth/me/' ? { id: 1, username: 'ana' } : path === 'auth/logout/' ? {} : org)
    vi.spyOn(api, 'all').mockResolvedValue([])
    render(<MemoryRouter initialEntries={['/org/o1']}><App/></MemoryRouter>)
    fireEvent.click(await screen.findByRole('button', { name: /Выйти/ }))
    expect(await screen.findByRole('heading', { name: /Следующий шаг/ })).toBeInTheDocument()
    expect(api.request).toHaveBeenCalledWith('auth/logout/', { method: 'POST' })
  })
  it('returns to login when the active session expires', async () => {
    vi.spyOn(api, 'request').mockImplementation(async path => path === 'auth/me/' ? { id: 1, username: 'ana' } : org)
    vi.spyOn(api, 'all').mockResolvedValue([])
    render(<MemoryRouter initialEntries={['/org/o1']}><App/></MemoryRouter>)
    await screen.findByRole('link', { name: /События/ })
    act(() => document.dispatchEvent(new Event('zetrix:session-expired')))
    expect(await screen.findByRole('heading', { name: /Следующий шаг/ })).toBeInTheDocument()
  })
  it('retries an organization load before showing projects', async () => {
    const request = vi.spyOn(api, 'request').mockImplementation(async path => {
      if (path === 'auth/me/') return { id: 1, username: 'ana' }
      if (path === 'organizations/o1/' && request.mock.calls.filter(([value]) => value === path).length === 1) throw new ApiError(0, 'network_error', 'Нет связи')
      return org
    })
    vi.spyOn(api, 'all').mockResolvedValue([])
    render(<MemoryRouter initialEntries={['/org/o1']}><App/></MemoryRouter>)
    expect(await screen.findByRole('alert')).toHaveTextContent('Нет связи')
    fireEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }))
    expect(await screen.findByRole('heading', { name: 'От вопроса — к сценарию.' })).toBeInTheDocument()
  })
})

describe('run history', () => {
  it('compares compatible saved results and returns to the selection prompt when deselected', async () => {
    const second = { ...base, id: 'run-2', results: { ...base.results, additional_total: '45.00', scenario_total: '345.00' } }
    vi.spyOn(api, 'all').mockResolvedValue([base, second])
    render(<MemoryRouter><History org={org}/></MemoryRouter>)
    await screen.findByRole('checkbox', { name: 'Сравнить расчёт run-1' })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Сравнить расчёт run-1' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Сравнить расчёт run-2' }))
    expect(screen.getByRole('table', { name: 'Сравнение сохранённых расчётов' })).toBeInTheDocument()
    expect(screen.getByText('45,00 USD')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Сравнить расчёт run-2' }))
    expect(screen.getByRole('status')).toHaveTextContent('Выберите минимум два результата')
  })
  it('rejects comparison when saved runs use different portfolio baselines', async () => {
    const first = { ...base, context: { portfolio_revision_id: 'portfolio-1' } }
    const second = { ...base, id: 'run-2', context: { portfolio_revision_id: 'portfolio-2' } }
    vi.spyOn(api, 'all').mockResolvedValue([first, second])
    render(<MemoryRouter><History org={org}/></MemoryRouter>)
    await screen.findByRole('checkbox', { name: 'Сравнить расчёт run-1' })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Сравнить расчёт run-1' }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'Сравнить расчёт run-2' }))
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('одна версия закупочного портфеля'))
  })
})
