import { cloneElement, isValidElement, useEffect, useId, useState, type ReactNode } from 'react'
import { api, errorMessage } from './api'
export function useResource<T>(path: string, list = false, refresh = 0) {
  const [state, setState] = useState<{ data?: T; error?: unknown; loading: boolean }>({ loading: true })
  useEffect(() => {
    const controller = new AbortController()
    setState({ loading: true })
    const request = list ? api.all(path, controller.signal) : api.request(path, { signal: controller.signal })
    request.then(data => { if (!controller.signal.aborted) setState({ data: data as T, loading: false }) }).catch(error => { if (!controller.signal.aborted) setState({ error, loading: false }) })
    return () => controller.abort()
  }, [path, list, refresh])
  return state
}
export function ErrorNotice({ error }: { error: unknown }) { return error ? <div className="error-notice" role="alert">{errorMessage(error)}</div> : null }
export function Loading({ label = 'Загрузка данных…' }: { label?: string }) { return <div className="loading-state" role="status"><span className="loading-dot" />{label}</div> }
export function Empty({ title, children }: { title: string; children?: ReactNode }) { return <div className="empty-state"><span className="empty-cross" aria-hidden="true">＋</span><h3>{title}</h3>{children}</div> }
export function Heading({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) { return <header className="page-heading"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{children && <p>{children}</p>}</header> }
export function RefreshError({ error, retry }: { error: unknown; retry: () => void }) { return <><ErrorNotice error={error} /><button className="secondary" onClick={retry}>Повторить загрузку</button></> }
export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  const hintId = useId()
  const control = isValidElement<Record<string, unknown>>(children)
    ? cloneElement(children, { 'aria-label': label, ...(hint ? { 'aria-describedby': hintId } : {}) })
    : children
  return <label className="field"><span>{label}</span>{control}{hint && <small id={hintId}>{hint}</small>}</label>
}
