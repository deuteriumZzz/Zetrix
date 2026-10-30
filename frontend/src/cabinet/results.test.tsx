import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { api } from './api'
import { RunPage } from './results'
import type { Organization, Run } from './types'

const org = { id: 'o1', name: 'Acme', role: 'analyst', created_at: '2026-10-16T00:00:00Z' } as Organization
const run = {
  id: 'run-1', created_at: org.created_at, project_id: 'project-1', revision_id: 'revision-1', status: 'succeeded',
  inputs: { kind: 'trade', monthly_cost: '300.00', exposure: '50.00', shock: '20.00', months: 3, currency: 'USD' },
  results: { baseline_total: '900.00', additional_total: '30.00', scenario_total: '930.00', additional_monthly: '10.00', exposed_monthly: '50.00', increase_percent: '3.33', currency: 'USD', line_impacts: [
    { line_id: 'line-1', affected: true, baseline_total: '300.00', additional_total: '30.00', scenario_total: '330.00' },
    { line_id: 'line-2', affected: false, baseline_total: '600.00', additional_total: '0.00', scenario_total: '600.00' },
  ] },
  context: { portfolio_revision_id: 'portfolio-1', portfolio_number: 2, monthly_total: '300.00', affected_line_ids: ['line-1'], lines: [
    { id: 'line-1', supplier: 'Acme Parts', country_code: 'US', category: 'Components', monthly_cost: '100.00', currency: 'USD' },
    { id: 'line-2', supplier: 'Beta Parts', country_code: 'DE', category: 'Materials', monthly_cost: '200.00', currency: 'USD' },
  ], evidence: { revision_id: 'evidence-1', title: 'Verified restriction', summary: 'Published', publication_status: 'current', sources: [{ publisher: 'Official Gazette', url: 'https://example.org', allowed_use: 'Link' }] } },
  engine_version: 'portfolio-cost-v1.0.0', assumptions: ['Deterministic direct costs.'],
} as Run
function showRun(role: Organization['role'] = 'analyst') {
  return render(<MemoryRouter initialEntries={['/org/o1/runs/run-1']}><Routes><Route path="/org/:orgId/runs/:runId" element={<RunPage org={{ ...org, role }}/>}/></Routes></MemoryRouter>)
}
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('saved result', () => {
  it('shows the saved portfolio, source backed event, and each line impact', async () => {
    vi.spyOn(api, 'request').mockResolvedValue(run)
    vi.spyOn(api, 'all').mockResolvedValue([])
    showRun()
    expect(await screen.findByRole('heading', { name: 'Закупочный портфель' })).toBeInTheDocument()
    expect(screen.getByText(/Версия 2/)).toBeInTheDocument()
    expect(screen.getByText('Verified restriction')).toBeInTheDocument()
    expect(screen.getByText('Official Gazette')).toBeInTheDocument()
    const rows = screen.getAllByRole('row')
    expect(rows.some(row => row.textContent?.includes('Acme Parts') && row.textContent.includes('30,00 USD'))).toBe(true)
    expect(rows.some(row => row.textContent?.includes('Beta Parts') && row.textContent.includes('0,00 USD'))).toBe(true)
  })
  it('offers authenticated CSV alongside JSON only to writers', async () => {
    vi.spyOn(api, 'request').mockResolvedValue(run)
    vi.spyOn(api, 'all').mockResolvedValue([])
    showRun()
    expect(await screen.findByRole('link', { name: /Скачать CSV/ })).toHaveAttribute('href', '/api/v2/organizations/o1/runs/run-1/csv/')
    expect(screen.getByRole('button', { name: /Скачать JSON/ })).toBeInTheDocument()
  })
  it('does not offer exports to a viewer', async () => {
    vi.spyOn(api, 'request').mockResolvedValue(run)
    vi.spyOn(api, 'all').mockResolvedValue([])
    showRun('viewer')
    await screen.findByRole('heading', { name: 'Последствия в цифрах.' })
    expect(screen.queryByRole('link', { name: /Скачать CSV/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Скачать JSON/ })).not.toBeInTheDocument()
  })
  it('creates and opens an immutable decision linked to the run', async () => {
    const decision = { id: 'decision-1', title: 'Get alternative quotes', note: 'Ask two suppliers.', run_ids: [run.id], project_id: run.project_id, created_at: org.created_at, snapshots: [run] }
    vi.spyOn(api, 'request').mockImplementation(async path => path.endsWith('decision-1/') ? decision : run)
    vi.spyOn(api, 'all').mockResolvedValueOnce([]).mockResolvedValueOnce([decision])
    const post = vi.spyOn(api, 'post').mockResolvedValue(decision)
    showRun()
    fireEvent.change(await screen.findByLabelText('Название решения'), { target: { value: 'Get alternative quotes' } })
    fireEvent.change(screen.getByLabelText('Обоснование решения'), { target: { value: 'Ask two suppliers.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить решение' }))
    await screen.findByRole('button', { name: /Get alternative quotes/ })
    expect(post.mock.calls[0][0]).toBe('organizations/o1/decisions/')
    expect(post.mock.calls[0][1]).toEqual({ title: 'Get alternative quotes', note: 'Ask two suppliers.', run_ids: [run.id] })
    expect(post.mock.calls[0][2]).toEqual(expect.objectContaining({ 'Idempotency-Key': expect.any(String) }))
    fireEvent.click(screen.getByRole('button', { name: /Get alternative quotes/ }))
    expect(await screen.findByText('Ask two suppliers.')).toBeInTheDocument()
    await waitFor(() => expect(api.request).toHaveBeenCalledWith('organizations/o1/decisions/decision-1/', expect.anything()))
  })
  it('reuses the decision idempotency key after a failed request', async () => {
    vi.spyOn(api, 'request').mockResolvedValue(run)
    vi.spyOn(api, 'all').mockResolvedValue([])
    const post = vi.spyOn(api, 'post').mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce({ id: 'decision-1' })
    showRun()
    fireEvent.change(await screen.findByLabelText('Название решения'), { target: { value: 'Keep stock' } })
    fireEvent.change(screen.getByLabelText('Обоснование решения'), { target: { value: 'Supply buffer.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить решение' }))
    await screen.findByRole('alert')
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить решение' }))
    await screen.findByText('Решение сохранено.')
    expect(post.mock.calls[0][2]).toEqual(post.mock.calls[1][2])
  })
})
