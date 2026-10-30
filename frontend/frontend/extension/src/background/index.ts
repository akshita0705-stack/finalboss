import { demoAssess } from '../shared/fixtures'
import { clearTabStatus, DEFAULTS, getSettings, patchSettings } from '../shared/storage'
import type { ToBackground } from '../shared/types'
import { openDashboard, openEvidence } from './alerts'
import { refreshActiveBadge, updateBadge } from './badge'
import { applyAssessment, flush, handleNavigation, pruneAlerts } from './pipeline'

// MV3 workers sleep: every listener is registered at top level, and state lives in chrome.storage.

chrome.runtime.onInstalled.addListener(async (d) => {
  await chrome.alarms.create('flush', { periodInMinutes: 1 })
  await chrome.alarms.create('prune', { periodInMinutes: 60 })
  if (d.reason === 'install') await chrome.runtime.openOptionsPage() // first-run consent screen
})

chrome.runtime.onStartup.addListener(async () => {
  await chrome.alarms.create('flush', { periodInMinutes: 1 })
  await chrome.alarms.create('prune', { periodInMinutes: 60 })
})

chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === 'flush') void flush()
  if (a.name === 'prune') void pruneAlerts()
})

chrome.webNavigation.onCommitted.addListener((d) => {
  if (d.frameId === 0) void handleNavigation(d.tabId, d.url, 'navigation', d.transitionQualifiers)
})
chrome.webNavigation.onErrorOccurred.addListener((d) => {
  if (d.frameId === 0) void handleNavigation(d.tabId, d.url, 'error')
})
chrome.webNavigation.onCompleted.addListener((d) => {
  if (d.frameId === 0) void updateBadge(d.tabId)
})

chrome.tabs.onActivated.addListener(({ tabId }) => void updateBadge(tabId))
chrome.tabs.onRemoved.addListener((tabId) => void clearTabStatus(tabId))
chrome.storage.onChanged.addListener((_c, area) => { if (area === 'local') void refreshActiveBadge() })

// Notification clicks open the evidence page; the id carries only host + finding id.
const parseNote = (id: string) => {
  const [, hostname, findingId, synthetic] = id.split('|')
  return { hostname, findingId: findingId || undefined, synthetic: synthetic === '1' }
}
const openFromNote = (id: string) => {
  if (!id.startsWith('tg|')) return
  const n = parseNote(id)
  void openEvidence({ ...n, severity: 'HIGH_RISK', reason: '', at: Date.now() })
}
chrome.notifications.onButtonClicked.addListener((id) => openFromNote(id))
chrome.notifications.onClicked.addListener((id) => openFromNote(id))

chrome.runtime.onMessage.addListener((msg: ToBackground) => {
  void (async () => {
    switch (msg.type) {
      case 'SET_PAUSED':
        await patchSettings({ paused: msg.paused })
        break
      case 'DEMO': {
        // Synthetic scenario on the active tab. Works without backend; clearly labelled as demo.
        const a = demoAssess(msg.hostname)
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
        if (a && tab?.id !== undefined) await applyAssessment(tab.id, a, true)
        break
      }
      case 'OPEN_EVIDENCE':
        await openEvidence(msg.assessment)
        break
      case 'OPEN_DASHBOARD':
        await openDashboard()
        break
      case 'FLUSH':
        await flush()
        break
      case 'DELETE_ALL': {
        const keep = await getSettings()
        await chrome.storage.local.clear()
        await chrome.storage.session.clear()
        // Keep connection settings, but drop consent so nothing is collected until re-confirmed.
        await patchSettings({ ...DEFAULTS, backendUrl: keep.backendUrl, dashboardUrl: keep.dashboardUrl })
        break
      }
    }
    await refreshActiveBadge()
  })()
})
