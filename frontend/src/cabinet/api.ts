import type { User } from './types'
type Envelope<T> = { success: boolean; data: T; error?: { code?: string; message?: string; field_errors?: unknown }; meta: { request_id?: string; count?: number; limit?: number; offset?: number } }
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public fields?: unknown, public requestId?: string) { super(message); this.name = 'ApiError' }
}
export class ApiClient {
  private csrf = ''
  async envelope<T>(path: string, options: RequestInit = {}): Promise<Envelope<T>> {
    const method = options.method || 'GET'
    if (!['GET', 'HEAD'].includes(method) && !this.csrf) await this.refreshCsrf()
    let response: Response
    try {
      response = await fetch(`/api/v2/${path}`, { ...options, credentials: 'same-origin', headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(!['GET', 'HEAD'].includes(method) ? { 'X-CSRFToken': this.csrf } : {}), ...options.headers } })
    } catch (error) {
      if (error && typeof error === 'object' && 'name' in error && error.name === 'AbortError') throw error
      throw new ApiError(0, 'network_error', 'Нет связи с сервером. Проверьте подключение и повторите запрос.')
    }
    let payload: Envelope<T>
    try { payload = await response.json() } catch { throw new ApiError(response.status, 'invalid_response', 'Сервер временно недоступен или вернул неожиданный ответ.') }
    if (!response.ok || !payload.success) {
      const failure = new ApiError(response.status, payload.error?.code || 'request_failed', payload.error?.message || 'Не удалось выполнить запрос.', payload.error?.field_errors, payload.meta?.request_id)
      if (failure.code === 'not_authenticated') document.dispatchEvent(new Event('zetrix:session-expired'))
      throw failure
    }
    return payload
  }
  async request<T>(path: string, options?: RequestInit): Promise<T> { return (await this.envelope<T>(path, options)).data }
  async refreshCsrf() { const data = await this.request<{ csrf_token: string }>('auth/csrf/'); this.csrf = data.csrf_token }
  async login(username: string, password: string): Promise<User> {
    await this.refreshCsrf()
    const data = await this.request<User & { csrf_token: string }>('auth/login/', { method: 'POST', body: JSON.stringify({ username, password }) })
    this.csrf = data.csrf_token
    return { id: data.id, username: data.username, is_staff: data.is_staff }
  }
  async all<T>(path: string, signal?: AbortSignal): Promise<T[]> {
    let records: T[] = [], offset = 0
    while (true) {
      const result = await this.envelope<T[]>(`${path}${path.includes('?') ? '&' : '?'}limit=50&offset=${offset}`, { signal })
      if (!Array.isArray(result.data)) throw new ApiError(502, 'invalid_response', 'Не удалось прочитать список.')
      records = [...records, ...result.data]
      if (records.length >= (result.meta.count ?? records.length) || result.data.length === 0) return records
      offset += result.data.length
      if (offset > 100000) throw new ApiError(400, 'list_limit', 'Слишком большой список. Обратитесь к администратору.')
    }
  }
  post<T>(path: string, body: unknown, headers?: Record<string, string>) { return this.request<T>(path, { method: 'POST', body: JSON.stringify(body), headers }) }
}
export const api = new ApiClient()
export const orgPath = (id: string) => `organizations/${encodeURIComponent(id)}/`
export function errorMessage(error: unknown) {
  if (!(error instanceof ApiError)) return error instanceof Error ? error.message : 'Не удалось выполнить действие.'
  const labels: Record<string, string> = { authentication_failed: 'Неверный логин или пароль.', not_authenticated: 'Сессия завершилась. Войдите снова.', permission_denied: 'Недостаточно прав для этого действия.', throttled: 'Слишком много запросов. Повторите через минуту.', not_found: 'Запись не найдена или доступ к ней закрыт.', conflict: 'Изменение конфликтует с сохранёнными данными. Обновите страницу и повторите.' }
  let details = ''
  if (error.fields && typeof error.fields === 'object') details = Object.entries(error.fields).map(([key, value]) => `${key}: ${typeof value === 'string' ? value : JSON.stringify(value)}`).join(' · ')
  return `${labels[error.code] || error.message}${details ? ` ${details}` : ''}${error.requestId ? ` · Код запроса: ${error.requestId}` : ''}`
}
