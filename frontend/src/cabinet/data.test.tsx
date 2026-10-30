import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { api, ApiError } from './api'
import { EventsPage, PortfolioPage, portfolioTotal } from './data'
import type { Organization } from './types'
vi.mock('./api', async importOriginal => ({ ...await importOriginal<typeof import('./api')>(), api: { all: vi.fn(), post: vi.fn() } }))
const org: Organization = { id: 'org', name: 'Team', role: 'analyst', created_at: '2026-10-17T00:00:00Z' }
function portfolio(role = org.role) {
  return render(<MemoryRouter initialEntries={['/projects/project/portfolio']}><Routes><Route path="/projects/:projectId/portfolio" element={<PortfolioPage org={{ ...org, role }}/>} /></Routes></MemoryRouter>)
}
beforeEach(() => { vi.mocked(api.all).mockResolvedValue([]); vi.mocked(api.post).mockReset() })
afterEach(() => { cleanup(); vi.clearAllMocks() })
describe('portfolio data screens', () => {
  it('sums preview money as exact cents', () => {
    expect(portfolioTotal([{ monthly_cost: '0.10' }, { monthly_cost: '0.20' }])).toBe('0.30')
    expect(portfolioTotal([{ monthly_cost: 'bad' }])).toBeNull()
  })
  it('keeps viewer read only and shows empty state', async () => {
    portfolio('viewer')
    expect(await screen.findByText('Портфель пока не создан')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Сохранить версию' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('CSV-файл')).not.toBeInTheDocument()
  })
  it('offers retry after loading fails', async () => {
    vi.mocked(api.all).mockRejectedValueOnce(new Error('Нет связи'))
    portfolio()
    expect(await screen.findByRole('alert')).toHaveTextContent('Нет связи')
    fireEvent.click(screen.getByRole('button', { name: 'Повторить загрузку' }))
    expect(await screen.findByText('Портфель пока не создан')).toBeInTheDocument()
  })
  it('saves manual lines without client-only ids', async () => {
    vi.mocked(api.post).mockResolvedValue({ number: 1 })
    portfolio()
    await screen.findByText('Портфель пока не создан')
    fireEvent.change(screen.getByLabelText('Поставщик 1'), { target: { value: 'Supplier' } })
    fireEvent.change(screen.getByLabelText('Страна 1'), { target: { value: 'US' } })
    fireEvent.change(screen.getByLabelText('Категория 1'), { target: { value: 'Hardware' } })
    fireEvent.change(screen.getByLabelText('Затраты 1'), { target: { value: '12.34' } })
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить версию' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('organizations/org/projects/project/portfolio/', { lines: [{ supplier: 'Supplier', country_code: 'US', category: 'Hardware', monthly_cost: '12.34', currency: 'USD' }] }))
  })
  it('renders CSV validation row errors without confirming', async () => {
    vi.mocked(api.post).mockRejectedValue(new ApiError(400, 'validation_error', 'Invalid', { rows: [{ row: 2, errors: { monthly_cost: ['Use decimal'] } }] }))
    portfolio()
    fireEvent.change(screen.getByLabelText('Содержимое CSV'), { target: { value: 'bad' } })
    fireEvent.click(screen.getByRole('button', { name: 'Проверить CSV' }))
    expect(await screen.findByText(/Строка 2/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Подтвердить импорт' })).not.toBeInTheDocument()
  })
  it('previews a CSV file and confirms an immutable portfolio version', async () => {
    const line = { id: 'line-1', supplier: 'Supplier', country_code: 'US', category: 'Hardware', monthly_cost: '12.34', currency: 'USD' }
    vi.mocked(api.post).mockResolvedValueOnce({ id: 'import-1', lines: [line], monthly_total: '12.34' }).mockResolvedValueOnce({ id: 'revision-1', number: 1 })
    portfolio()
    const csv = 'supplier,country_code,category,monthly_cost,currency\nSupplier,US,Hardware,12.34,USD'
    const file = new File([csv], 'purchases.csv', { type: 'text/csv' })
    Object.defineProperty(file, 'text', { value: async () => csv })
    fireEvent.change(screen.getByLabelText('CSV-файл'), { target: { files: [file] } })
    await waitFor(() => expect(screen.getByLabelText('Содержимое CSV')).toHaveValue(csv))
    fireEvent.click(screen.getByRole('button', { name: 'Проверить CSV' }))
    expect(await screen.findByText('Предпросмотр · 1 строк')).toBeInTheDocument()
    expect(api.post).toHaveBeenCalledWith('organizations/org/projects/project/portfolio/preview/', { csv })
    fireEvent.click(screen.getByRole('button', { name: 'Подтвердить импорт' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('organizations/org/projects/project/portfolio/imports/import-1/confirm/', {}))
    expect(await screen.findByText('Версия 1 сохранена.')).toBeInTheDocument()
  })
  it('lets an analyst add and remove draft rows before saving', async () => {
    vi.mocked(api.post).mockResolvedValue({ number: 1 })
    portfolio()
    await screen.findByText('Портфель пока не создан')
    fireEvent.click(screen.getByRole('button', { name: 'Добавить строку' }))
    expect(screen.getByLabelText('Поставщик 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Удалить строку 1' }))
    expect(screen.queryByLabelText('Поставщик 2')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Поставщик 1'), { target: { value: 'Remaining supplier' } })
    fireEvent.change(screen.getByLabelText('Страна 1'), { target: { value: 'DE' } })
    fireEvent.change(screen.getByLabelText('Категория 1'), { target: { value: 'Materials' } })
    fireEvent.change(screen.getByLabelText('Затраты 1'), { target: { value: '20.00' } })
    fireEvent.click(screen.getByRole('button', { name: 'Сохранить версию' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('organizations/org/projects/project/portfolio/', { lines: [{ supplier: 'Remaining supplier', country_code: 'DE', category: 'Materials', monthly_cost: '20.00', currency: 'USD' }] }))
  })
})
describe('event registry', () => {
  it('keeps a withdrawn event visible with its historical status', async () => {
    const historical = { revision_id: 'r', title: 'Withdrawn notice', summary: 'Previously reviewed', number: 1, event_kind: 'trade_restriction', country_codes: ['US'], effective_at: '2026-10-17T00:00:00Z', provenance: 'Review log', sources: [], publication_status: 'withdrawn' }
    vi.mocked(api.all).mockResolvedValue([{ id: 'e', published_revision: null, historical_revision: historical }])
    render(<EventsPage user={{ id: 1, username: 'reader', is_staff: false }}/>)
    expect(await screen.findByText('Withdrawn notice')).toBeInTheDocument()
    expect(screen.getByText('Отозвано')).toBeInTheDocument()
  })
  it('hides curators forms for ordinary users', async () => {
    render(<EventsPage user={{ id: 1, username: 'reader', is_staff: false }}/>)
    expect(await screen.findByText('Опубликованных событий пока нет')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Создать черновик' })).not.toBeInTheDocument()
    expect(api.all).toHaveBeenCalledTimes(1)
  })
  it('makes explicit publishing available only to staff', async () => {
    const revision = { revision_id: 'r', title: 'Example', summary: 'Checked summary', number: 1, event_kind: 'other', country_codes: ['US'], effective_at: '2026-10-17T00:00:00Z', provenance: 'Manual verification', sources: [], publication_status: 'draft' }
    vi.mocked(api.all).mockImplementation(async path => path === 'evidence/events/' ? [{ id: 'e', latest_revision: revision, published_revision: null }] : [])
    vi.mocked(api.post).mockResolvedValue({})
    render(<EventsPage user={{ id: 1, username: 'curator', is_staff: true }}/>)
    fireEvent.click(await screen.findByRole('button', { name: 'Опубликовать версию 1' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('evidence/events/e/publish/', { revision_id: 'r' }))
  })
  it('creates a reviewed revision from a published event and retains its sources', async () => {
    const published = { revision_id: 'r1', title: 'Example', summary: 'Checked summary', number: 1, event_kind: 'other', country_codes: ['US'], effective_at: '2026-10-17T00:00:00Z', provenance: 'Manual verification', sources: [{ id: 'source-1', publisher: 'Gazette', url: 'https://example.org', allowed_use: 'Link' }], publication_status: 'current' }
    vi.mocked(api.all).mockImplementation(async path => path === 'evidence/sources/' ? published.sources : [{ id: 'event-1', latest_revision: published, published_revision: published }])
    vi.mocked(api.post).mockResolvedValue({})
    render(<EventsPage user={{ id: 1, username: 'curator', is_staff: true }}/>)
    fireEvent.click(await screen.findByRole('button', { name: 'Создать новую версию' }))
    const editor = screen.getByText('Новая версия события').closest('.revision-editor') as HTMLElement
    expect(await within(editor).findByRole('checkbox', { name: /Gazette/ })).toBeChecked()
    fireEvent.change(within(editor).getByLabelText('Краткое описание'), { target: { value: 'Updated summary' } })
    fireEvent.click(within(editor).getByRole('button', { name: 'Сохранить новую версию' }))
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('evidence/events/event-1/revisions/', expect.objectContaining({ summary: 'Updated summary', source_ids: ['source-1'] })))
    expect(screen.queryByRole('button', { name: 'Сохранить новую версию' })).not.toBeInTheDocument()
  })
})
