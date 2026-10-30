import { useAuthStore } from '@/store/auth'

export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'
const V1 = `${API_BASE}/api/v1`

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

/** FastAPI returns `detail` as a string or as a list of validation errors. */
function messageFrom(body: unknown, fallback: string): string {
  const d = (body as { detail?: unknown } | null)?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d) && d.length) return d.map((e: { msg?: string }) => e.msg ?? 'Invalid input').join('; ')
  return fallback
}

export async function api<T>(path: string, init: RequestInit & { auth?: boolean } = {}): Promise<T> {
  const { auth = true, headers, ...rest } = init
  const h = new Headers(headers)
  if (rest.body && !h.has('Content-Type')) h.set('Content-Type', 'application/json')
  const token = useAuthStore.getState().token
  if (auth && token) h.set('Authorization', `Bearer ${token}`)

  let res: Response
  try {
    res = await fetch(`${V1}${path}`, { ...rest, headers: h })
  } catch {
    throw new ApiError(0, 'Cannot reach the TraceGuard backend. Is it running?')
  }
  if (res.status === 401 && auth) useAuthStore.getState().logout()
  const body = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, messageFrom(body, `Request failed (${res.status})`))
  return body as T
}

export interface User { id: string; email: string; full_name: string | null; role: string; is_active: boolean; created_at: string }
export interface Token { access_token: string; token_type: string; expires_in: number; role: string; user_id?: string }

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    api<User>('/auth/register', { method: 'POST', auth: false, body: JSON.stringify({ email, password, full_name: full_name || null }) }),
  login: (email: string, password: string) =>
    api<Token>('/auth/login', { method: 'POST', auth: false, body: JSON.stringify({ email, password }) }),
  me: () => api<User>('/auth/me'),
}

export interface ApiKeyInfo {
  id: string; installation_id: string; name: string; api_key: string | null
  is_active: boolean; created_at: string; last_used_at: string | null
}

export const keysApi = {
  create: (installation_id: string, name = 'Chrome Extension') =>
    api<ApiKeyInfo>('/auth/api-keys', { method: 'POST', body: JSON.stringify({ installation_id, name }) }),
}

import type { DashboardSummary } from '@/types/dashboard'

export const dashboardApi = {
  summary: (days = 7) => api<DashboardSummary>(`/dashboard/summary?days=${days}`),
}
