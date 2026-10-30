import type { Assessment, QueueItem, Settings, TabStatus } from './types'

export const DEFAULTS: Settings = {
  consented: false,
  paused: false,
  demoMode: true,
  backendUrl: 'http://localhost:8000',
  dashboardUrl: 'http://localhost:5173',
  token: '',
  excluded: [],
  retentionDays: 30,
  reduceEffects: false,
  notifySeverities: ['HIGH_RISK', 'SUSPICIOUS'],
  backendOk: null,
}

export async function getSettings(): Promise<Settings> {
  const r = await chrome.storage.local.get('settings')
  return { ...DEFAULTS, ...(r.settings ?? {}) }
}

export async function patchSettings(p: Partial<Settings>): Promise<Settings> {
  const s = { ...(await getSettings()), ...p }
  await chrome.storage.local.set({ settings: s })
  return s
}

export async function getAlerts(): Promise<Assessment[]> {
  return (await chrome.storage.local.get('alerts')).alerts ?? []
}

export async function addAlert(a: Assessment) {
  const list = [a, ...(await getAlerts())].slice(0, 50)
  await chrome.storage.local.set({ alerts: list })
}

export async function getQueue(): Promise<QueueItem[]> {
  return (await chrome.storage.local.get('queue')).queue ?? []
}

export const setQueue = (queue: QueueItem[]) => chrome.storage.local.set({ queue })

// Per-tab state lives in session storage: it survives service-worker restarts but not the browser session.
export async function getTabStatus(tabId: number): Promise<TabStatus | undefined> {
  return (await chrome.storage.session.get(`tab:${tabId}`))[`tab:${tabId}`]
}
export const setTabStatus = (tabId: number, s: TabStatus) => chrome.storage.session.set({ [`tab:${tabId}`]: s })
export const clearTabStatus = (tabId: number) => chrome.storage.session.remove([`tab:${tabId}`, `last:${tabId}`])

export async function getLastHost(tabId: number): Promise<string | undefined> {
  return (await chrome.storage.session.get(`last:${tabId}`))[`last:${tabId}`]
}
export const setLastHost = (tabId: number, host: string) => chrome.storage.session.set({ [`last:${tabId}`]: host })

/** Timestamp map used for dedupe and alert rate-limiting. */
export async function touch(bucket: 'seen' | 'notified', host: string, windowMs: number): Promise<boolean> {
  const map: Record<string, number> = (await chrome.storage.session.get(bucket))[bucket] ?? {}
  const now = Date.now()
  if (map[host] && now - map[host] < windowMs) return false
  map[host] = now
  for (const k of Object.keys(map)) if (now - map[k] > 3600_000) delete map[k]
  await chrome.storage.session.set({ [bucket]: map })
  return true
}

export function evidenceUrl(s: Settings, a: Assessment): string {
  const base = s.dashboardUrl.replace(/\/$/, '')
  // Demo findings have no backend record, so point at the demo simulator.
  return a.synthetic || !a.findingId ? `${base}/app/site-check` : `${base}/app/findings/${encodeURIComponent(a.findingId)}`
}
