import { useState, type FormEvent } from 'react'
import { api, orgPath } from './api'
import { roleNames } from './domain'
import type { Member, Organization, Role } from './types'
import { ErrorNotice, Field, Heading, Loading, RefreshError, useResource } from './ui'
export function Team({ org, onMembershipChange }: { org: Organization; onMembershipChange: () => void }) {
  const [refresh, setRefresh] = useState(0), state = useResource<Member[]>(`${orgPath(org.id)}members/`, true, refresh)
  const [error, setError] = useState<unknown>(), [pending, setPending] = useState(false)
  const manage = org.role === 'owner' || org.role === 'admin'
  const roles = Object.entries(roleNames).filter(([role]) => org.role === 'owner' || role !== 'owner')
  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget, values = new FormData(form); setPending(true); setError(undefined)
    try { await api.post(`${orgPath(org.id)}members/`, { username: String(values.get('username')).trim(), role: values.get('role') }); form.reset(); setRefresh(x => x + 1) } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  async function update(member: Member, changes: { role?: Role; active?: boolean }) {
    setPending(true); setError(undefined)
    try { await api.request(`${orgPath(org.id)}members/${member.id}/`, { method: 'PATCH', body: JSON.stringify(changes) }); setRefresh(x => x + 1); onMembershipChange() } catch (failure) { setError(failure) } finally { setPending(false) }
  }
  return <><Heading eyebrow="03 / TEAM" title="Общее пространство решений.">Участники организации и права доступа. В команде всегда должен оставаться хотя бы один активный владелец.</Heading><ErrorNotice error={error}/>{state.loading ? <Loading/> : state.error ? <RefreshError error={state.error} retry={() => setRefresh(x => x + 1)}/> : <div className="panel table-scroll"><table><caption className="sr-only">Участники организации</caption><thead><tr><th>Участник</th><th>Роль</th><th>Доступ</th></tr></thead><tbody>{state.data?.map(member => { const editable = manage && (member.role !== 'owner' || org.role === 'owner'); return <tr key={member.id}><th>{member.username}</th><td>{editable ? <select aria-label={`Роль ${member.username}`} value={member.role} disabled={pending} onChange={event => update(member, { role: event.target.value as Role })}>{roles.map(([role, label]) => <option key={role} value={role}>{label}</option>)}</select> : roleNames[member.role]}</td><td>{editable ? <button className="secondary" disabled={pending} onClick={() => update(member, { active: !member.active })}>{member.active ? 'Отключить доступ' : 'Восстановить доступ'}</button> : member.active ? 'Активен' : 'Отключён'}</td></tr>})}</tbody></table></div>}{manage && <form className="panel editor" onSubmit={add}><h2>Добавить участника</h2><p className="muted">Укажите имя уже существующей учётной записи. Письмо автоматически не отправляется.</p><div className="input-grid"><Field label="Имя пользователя"><input name="username" required maxLength={150} autoComplete="off"/></Field><Field label="Роль"><select name="role" defaultValue="analyst">{roles.map(([role, label]) => <option key={role} value={role}>{label}</option>)}</select></Field></div><button className="primary" disabled={pending}>{pending ? 'Сохранение…' : 'Добавить в команду ↗'}</button></form>}<div className="disclosure"><span>i</span><p>Аналитик создаёт проекты, версии и расчёты. Наблюдатель читает сохранённые данные. Администратор управляет участниками, владелец — также другими владельцами.</p></div></>
}
