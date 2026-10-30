import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError } from './api'
const response = (data: unknown, status = 200, meta = {}) => new Response(JSON.stringify({ success: status < 400, data: status < 400 ? data : null, error: status >= 400 ? data : null, meta }), { status })
afterEach(() => { vi.unstubAllGlobals() })
describe('session API', () => {
  it('obtains CSRF and replaces it after login, never persisting tokens', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({ csrf_token: 'before' })).mockResolvedValueOnce(response({ id: 1, username: 'ana', csrf_token: 'after' })).mockResolvedValueOnce(response(null))
    vi.stubGlobal('fetch', fetcher)
    const client = new ApiClient()
    await client.login('ana', 'password')
    await client.request('auth/logout/', { method: 'POST' })
    expect(fetcher.mock.calls[1][1].headers['X-CSRFToken']).toBe('before')
    expect(fetcher.mock.calls[2][1].headers['X-CSRFToken']).toBe('after')
    expect(fetcher.mock.calls[1][1].credentials).toBe('same-origin')
  })
  it('preserves API errors and request identifiers', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ code: 'permission_denied', message: 'Denied' }, 403, { request_id: 'r1' })))
    await expect(new ApiClient().request('organizations/')).rejects.toMatchObject({ status: 403, code: 'permission_denied', requestId: 'r1' })
  })
  it('uses all pages, not just the first twenty records', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response([{ id: '1' }], 200, { count: 2, limit: 1, offset: 0 })).mockResolvedValueOnce(response([{ id: '2' }], 200, { count: 2, limit: 1, offset: 1 }))
    vi.stubGlobal('fetch', fetcher)
    expect(await new ApiClient().all('organizations/')).toHaveLength(2)
    expect(fetcher.mock.calls[1][0]).toContain('offset=1')
  })
  it('rejects non-JSON backend failures with a useful error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>unavailable</html>', { status: 502 })))
    await expect(new ApiClient().request('auth/me/')).rejects.toBeInstanceOf(ApiError)
  })
  it('turns a broken connection into a retryable network error while preserving cancellation', async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch')).mockRejectedValueOnce(new DOMException('Aborted', 'AbortError'))
    vi.stubGlobal('fetch', fetcher)
    const client = new ApiClient()
    await expect(client.request('organizations/')).rejects.toMatchObject({ code: 'network_error', status: 0 })
    await expect(client.request('organizations/')).rejects.toMatchObject({ name: 'AbortError' })
  })
  it('broadcasts an expired session so open workspace screens can return to login', async () => {
    const expired = vi.fn()
    document.addEventListener('zetrix:session-expired', expired, { once: true })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ code: 'not_authenticated', message: 'Sign in' }, 401)))
    await expect(new ApiClient().request('organizations/')).rejects.toMatchObject({ code: 'not_authenticated' })
    expect(expired).toHaveBeenCalledTimes(1)
  })
  it('rejects a malformed paginated list instead of showing incomplete data', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ unexpected: true })))
    await expect(new ApiClient().all('organizations/')).rejects.toMatchObject({ code: 'invalid_response' })
  })
})
