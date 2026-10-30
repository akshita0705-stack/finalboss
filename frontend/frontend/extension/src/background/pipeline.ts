import { demoAssess } from '../shared/fixtures'
import { hostFromUrl, isExcluded } from '../shared/normalize'
import {
  addAlert, getLastHost, getQueue, getSettings, patchSettings, setLastHost, setQueue, setTabStatus, touch,
} from '../shared/storage'
import type { Assessment, NavEvent, QueueItem, Severity } from '../shared/types'
import { notify, showBanner } from './alerts'
import { refreshActiveBadge, updateBadge } from './badge'

const DEDUPE_MS = 30_000
const MAX_QUEUE = 200
const SEVERITIES: Severity[] = ['HIGH_RISK', 'SUSPICIOUS', 'NEEDS_REVIEW', 'LOW_OBSERVED_RISK', 'UNKNOWN']

export async function handleNavigation(tabId: number, url: string, type: NavEvent['event_type'], qualifiers: string[] = []) {
  const s = await getSettings()
  if (!s.consented || s.paused) return
  const tab = await chrome.tabs.get(tabId).catch(() => null)
  if (!tab || tab.incognito) return // incognito is skipped
  const host = hostFromUrl(url) // null for chrome://, file://, extension pages, etc.
  if (!host || isExcluded(host, s.excluded)) return

  const prev = await getLastHost(tabId)
  await setLastHost(tabId, host)
  if (!(await touch('seen', `${tabId}|${host}`, DEDUPE_MS))) return

  const isRedirect = qualifiers.some((q) => q === 'server_redirect' || q === 'client_redirect')
  const event: NavEvent = {
    event_id: crypto.randomUUID(), // idempotency key for retries
    hostname: host,
    event_type: type,
    timestamp: new Date().toISOString(),
    ...(isRedirect && prev && prev !== host ? { redirect_from_host: prev } : {}),
  }

  if (s.demoMode) {
    const a = demoAssess(host)
    if (a) await applyAssessment(tabId, a)
    else await setTabStatus(tabId, { state: 'skipped' }) // demo mode only knows fixtures: "not assessed", not "safe"
    await updateBadge(tabId)
    return
  }

  await setTabStatus(tabId, { state: 'pending' })
  const queue = await getQueue()
  queue.push({ event, tabId, attempts: 0, nextAt: 0 })
  await setQueue(queue.slice(-MAX_QUEUE))
  await flush()
}

export async function applyAssessment(tabId: number, a: Assessment, force = false) {
  await setTabStatus(tabId, { state: 'assessed', assessment: a })
  if (a.severity !== 'LOW_OBSERVED_RISK') await addAlert(a)
  await updateBadge(tabId)
  await notify(a, force)
  await showBanner(tabId, a)
}

let flushing = false

/** Sends due events with a bearer token. Failures back off exponentially; the alarm retries later. */
export async function flush() {
  if (flushing) return
  flushing = true
  try {
    const s = await getSettings()
    if (s.demoMode || !s.token) return
    const queue = await getQueue()
    const now = Date.now()
    const rest: QueueItem[] = []
    for (const item of queue) {
      if (item.nextAt > now) { rest.push(item); continue }
      try {
        const res = await fetch(`${s.backendUrl.replace(/\/$/, '')}/api/v1/extension/events`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${s.token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(item.event),
        })
        if (!res.ok) throw new Error(String(res.status))
        const a = parseAssessment(await res.json().catch(() => null), item.event.hostname)
        if (a) await applyAssessment(item.tabId, a)
        else await setTabStatus(item.tabId, { state: 'skipped' })
        if (s.backendOk !== true) await patchSettings({ backendOk: true })
      } catch {
        const attempts = item.attempts + 1
        rest.push({ ...item, attempts, nextAt: now + Math.min(5 * 60_000, 2 ** attempts * 5_000) })
        await setTabStatus(item.tabId, { state: 'unreachable' })
        if (s.backendOk !== false) await patchSettings({ backendOk: false })
      }
    }
    await setQueue(rest)
    await refreshActiveBadge()
  } finally {
    flushing = false
  }
}

/** Assumed response: { assessment: { severity, reason, finding_id? , redirects? } }. Anything else is "not assessed". */
function parseAssessment(body: unknown, hostname: string): Assessment | null {
  const raw = (body as { assessment?: Record<string, unknown> } | null)?.assessment
  if (!raw || typeof raw.severity !== 'string' || !SEVERITIES.includes(raw.severity as Severity)) return null
  return {
    hostname,
    severity: raw.severity as Severity,
    reason: typeof raw.reason === 'string' ? raw.reason : 'No reason provided.',
    findingId: typeof raw.finding_id === 'string' ? raw.finding_id : undefined,
    redirects: Array.isArray(raw.redirects) ? raw.redirects.filter((x): x is string => typeof x === 'string') : undefined,
    at: Date.now(),
    synthetic: false,
  }
}

export async function pruneAlerts() {
  const s = await getSettings()
  const cutoff = Date.now() - s.retentionDays * 86_400_000
  const { alerts = [] } = await chrome.storage.local.get('alerts')
  await chrome.storage.local.set({ alerts: (alerts as Assessment[]).filter((a) => a.at >= cutoff) })
}
