import { SEV } from '../shared/severity'
import { evidenceUrl, getSettings, touch } from '../shared/storage'
import type { Assessment, ToContent } from '../shared/types'

const NOTIFY_WINDOW_MS = 10 * 60_000

/** chrome.notifications for configured severities. Deduped and rate-limited per host unless `force` (demo). */
export async function notify(a: Assessment, force = false) {
  const s = await getSettings()
  if (!s.notifySeverities.includes(a.severity)) return
  if (!force && !(await touch('notified', a.hostname, NOTIFY_WINDOW_MS))) return
  const id = `tg|${a.hostname}|${a.findingId ?? ''}|${a.synthetic ? 1 : 0}`
  await chrome.notifications.create(id, {
    type: 'basic',
    iconUrl: 'icons/icon128.png',
    title: `☠ TraceGuard: ${SEV[a.severity].label}`,
    message: `${a.hostname}\n${a.reason}${a.synthetic ? ' (demo)' : ''}`,
    buttons: [{ title: 'View evidence' }],
    requireInteraction: a.severity === 'HIGH_RISK',
  })
}

export async function openEvidence(a: Assessment) {
  const s = await getSettings()
  await chrome.tabs.create({ url: evidenceUrl(s, a) })
}

export async function openDashboard() {
  const s = await getSettings()
  await chrome.tabs.create({ url: s.dashboardUrl })
}

/**
 * Optional in-page warning. Injected only after an alert, only on that tab, and only if the user granted
 * site access in Options. It never reads page content and never blocks navigation.
 */
export async function showBanner(tabId: number, a: Assessment) {
  if (a.severity !== 'HIGH_RISK' && a.severity !== 'SUSPICIOUS') return
  try {
    const tab = await chrome.tabs.get(tabId)
    if (!tab.url || !/^https?:/.test(tab.url)) return
    const origin = `${new URL(tab.url).origin}/*`
    if (!(await chrome.permissions.contains({ origins: [origin] }))) return
    await chrome.scripting.executeScript({ target: { tabId }, files: ['content.js'] })
    const msg: ToContent = { type: 'SHOW_BANNER', assessment: a }
    await chrome.tabs.sendMessage(tabId, msg)
  } catch { /* tab navigated away or injection not allowed */ }
}
