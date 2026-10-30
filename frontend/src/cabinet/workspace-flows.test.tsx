import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { App, Logout } from './App'
import { EventsPage } from './data'
import { Team } from './team'
import { api, ApiError } from './api'
import type { Organization } from './types'

const org: Organization = { id: 'o1', name: 'Acme', role: 'owner', created_at: '2026-10-17T00:00:00Z' }
const source = { id: 'source-1', publisher: 'Official Gazette', url: 'https://example.org/notice', allowed_use: 'Link only' }
const draft = { id: 'revision-1', revision_id: 'revision-1', number: 1, title: 'Import notice', summary: 'Reviewed restriction', event_kind: 'trade_restriction', country_codes: ['US'], effective_at: '2026-10-17T00:00:00Z', provenance: 'Manual review', sources: [source], publication_status: 'draft' }
afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('event curation', () => {
  it('lets staff register a source, create a draft, and explicitly publish it', async () => {
    let sources: typeof source[] = []
    let events: { id: string; latest_revision: typeof draft; published_revision: typeof draft | null }[] = []
    vi.spyOn(api, 'all').mockImplementation(async path => path === 'evidence/sources/' ? sources : events)
    const post = vi.spyOn(api, 'post').mockImplementation(async path => {
      if (path === 'evidence/sources/') sources = [source]
      if (path === 'evidence/events/') events = [{ id: 'event-1', latest_revision: draft, published_revision: null }]
      if (path === 'evidence/events/event-1/publish/') events = [{ id: 'event-1', latest_revision: { ...draft, publication_status: 'current' }, published_revision: { ...draft, publication_status: 'current' } }]
      return {}
    })
    render(<EventsPage user={{ id: 1, username: 'curator', is_staff: true }}/>)
    await screen.findByText('В реестре пока нет событий')
    fireEvent.click(screen.getByText('Добавить источник', { selector: 'summary' }))
    fireEvent.change(screen.getByLabelText('Издатель / организация'), { target: { value: source.publisher } })
    fireEvent.change(screen.getByLabelText('Ссылка на источник'), { target: { value: source.url } })
    fireEvent.change(screen.getByLabelText('Разрешённое использование'), { target: { value: source.allowed_use } })
    fireEvent.click(screen.getByRole('button', { name: 'Добавить источник' }))
    await waitFor(() => expect(post).toHaveBeenCalledWith('evidence/sources/', { publisher: source.publisher, url: source.url, allowed_use: source.allowed_use }))
    fireEvent.click(screen.getByText('Создать событие'))
    await screen.findByRole('checkbox', { name: /Official Gazette/ })
    fireEvent.change(screen.getByLabelText('Заголовок события'), { target: { value: draft.title } })
    fireEvent.change(screen.getByLabelText('Краткое описание'), { target: { value: draft.summary } })
    fireEvent.change(screen.getByLabelText('Коды стран'), { target: { value: 'US' } })
    fireEvent.change(screen.getByLabelText('Дата и время вступления в силу'), { target: { value: '2026-10-17T08:00' } })
    fireEvent.change(screen.getByLabelText('Основания и способ проверки'), { target: { value: draft.provenance } })
    fireEvent.click(screen.getByRole('checkbox', { name: /Official Gazette/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Создать черновик' }))
    await screen.findByRole('button', { name: 'Опубликовать версию 1' })
    expect(post).toHaveBeenCalledWith('evidence/events/', expect.objectContaining({ title: draft.title, country_codes: ['US'], source_ids: [source.id] }))
    fireEvent.click(screen.getByRole('button', { name: 'Опубликовать версию 1' }))
    await waitFor(() => expect(post).toHaveBeenCalledWith('evidence/events/event-1/publish/', { revision_id: draft.revision_id }))
    expect(await screen.findByText('Опубликовано')).toBeInTheDocument()
  })
  it('rejects an authenticated source URL and preserves an existing publication after a failed revoke', async () => {
    vi.spyOn(api, 'all').mockImplementation(async path => path === 'evidence/sources/' ? [source] : [{ id: 'event-1', latest_revision: { ...draft, publication_status: 'current' }, published_revision: { ...draft, publication_status: 'current' } }])
    const post = vi.spyOn(api, 'post').mockRejectedValue(new ApiError(400, 'validation_error', 'Cannot revoke'))
    render(<EventsPage user={{ id: 1, username: 'curator', is_staff: true }}/>)
    fireEvent.click(screen.getByText('Добавить источник', { selector: 'summary' }))
    fireEvent.change(screen.getByLabelText('Издатель / организация'), { target: { value: 'Private' } })
    fireEvent.change(screen.getByLabelText('Ссылка на источник'), { target: { value: 'https://user:password@example.org/notice' } })
    fireEvent.change(screen.getByLabelText('Разрешённое использование'), { target: { value: 'Link' } })
    fireEvent.click(screen.getByRole('button', { name: 'Добавить источник' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('HTTP(S)-адрес без логина и пароля')
    expect(post).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText('Отозвать публикацию'))
    fireEvent.change(screen.getByLabelText('Причина отзыва'), { target: { value: 'Superseded by official correction' } })
    fireEvent.click(screen.getByRole('button', { name: 'Подтвердить отзыв' }))
    await waitFor(() => expect(post).toHaveBeenCalledWith('evidence/events/event-1/revoke/', { reason: 'Superseded by official correction' }))
    expect(screen.getByText('Опубликовано')).toBeInTheDocument()
  })
})

describe('team management', () => {
  const owner = { id: 'member-owner', username: 'founder', role: 'owner', active: true, created_at: org.created_at }
  const analyst = { id: 'member-analyst', username: 'ana', role: 'analyst', active: true, created_at: org.created_at }
  it('lets an owner add a member and update role and access', async () => {
    vi.spyOn(api, 'all').mockResolvedValue([owner, analyst])
    const post = vi.spyOn(api, 'post').mockResolvedValue({})
    const patch = vi.spyOn(api, 'request').mockResolvedValue({})
    const changed = vi.fn()
    render(<Team org={org} onMembershipChange={changed}/>)
    await screen.findByRole('table', { name: 'Участники организации' })
    fireEvent.change(screen.getByLabelText('Имя пользователя'), { target: { value: '  newuser  ' } })
    fireEvent.change(screen.getByLabelText('Роль'), { target: { value: 'viewer' } })
    fireEvent.click(screen.getByRole('button', { name: /Добавить в команду/ }))
    await waitFor(() => expect(post).toHaveBeenCalledWith('organizations/o1/members/', { username: 'newuser', role: 'viewer' }))
    fireEvent.change(screen.getByLabelText('Роль ana'), { target: { value: 'admin' } })
    await waitFor(() => expect(patch).toHaveBeenCalledWith('organizations/o1/members/member-analyst/', { method: 'PATCH', body: JSON.stringify({ role: 'admin' }) }))
    const row = screen.getByRole('row', { name: /ana/ })
    fireEvent.click(within(row).getByRole('button', { name: 'Отключить доступ' }))
    await waitFor(() => expect(patch).toHaveBeenCalledWith('organizations/o1/members/member-analyst/', { method: 'PATCH', body: JSON.stringify({ active: false }) }))
    expect(changed).toHaveBeenCalledTimes(2)
  })
  it('keeps an administrator from editing an owner and hides controls from viewers', async () => {
    vi.spyOn(api, 'all').mockResolvedValue([owner, analyst])
    const { rerender } = render(<Team org={{ ...org, role: 'admin' }} onMembershipChange={vi.fn()}/>)
    await screen.findByRole('table', { name: 'Участники организации' })
    expect(screen.queryByLabelText('Роль founder')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Роль ana')).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Владелец' })).not.toBeInTheDocument()
    rerender(<Team org={{ ...org, role: 'viewer' }} onMembershipChange={vi.fn()}/>)
    expect(screen.queryByRole('button', { name: /Добавить в команду/ })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Роль ana')).not.toBeInTheDocument()
  })
  it('shows a failed role update and leaves the member visible', async () => {
    vi.spyOn(api, 'all').mockResolvedValue([analyst])
    vi.spyOn(api, 'request').mockRejectedValue(new ApiError(403, 'permission_denied', 'Denied'))
    const changed = vi.fn()
    render(<Team org={org} onMembershipChange={changed}/>)
    fireEvent.change(await screen.findByLabelText('Роль ana'), { target: { value: 'viewer' } })
    expect(await screen.findByRole('alert')).toHaveTextContent('Недостаточно прав')
    expect(screen.getByText('ana')).toBeInTheDocument()
    expect(changed).not.toHaveBeenCalled()
  })
})

describe('cabinet session', () => {
  it('shows login when the session has expired', async () => {
    vi.spyOn(api, 'request').mockRejectedValue(new ApiError(401, 'not_authenticated', 'Login required'))
    render(<MemoryRouter initialEntries={['/org/o1']}><App/></MemoryRouter>)
    expect(await screen.findByRole('heading', { name: /Следующий шаг/ })).toBeInTheDocument()
  })
  it('preserves the signed-in session when logout fails', async () => {
    vi.spyOn(api, 'request').mockRejectedValue(new ApiError(0, 'network_error', 'Нет связи'))
    const onLogout = vi.fn()
    render(<Logout onLogout={onLogout}/>)
    fireEvent.click(screen.getByRole('button', { name: /Выйти/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Нет связи')
    expect(onLogout).not.toHaveBeenCalled()
  })
})
