import { SEV } from '../shared/severity'
import { getSettings, getTabStatus } from '../shared/storage'

/** Badge text/colour for a tab. Missing results never show a reassuring tick. */
export async function updateBadge(tabId: number) {
  const s = await getSettings()
  let text = '', color = '#6b7280'
  if (!s.consented) { text = ''; }
  else if (s.paused) { text = 'II'; color = '#6b7280' }
  else if (!s.demoMode && (!s.token || s.backendOk === false)) { text = 'OFF'; color = '#6b7280' }
  else {
    const st = await getTabStatus(tabId)
    if (st?.state === 'assessed' && st.assessment) {
      const m = SEV[st.assessment.severity]
      text = m.badge; color = m.badgeColor
    } else if (st?.state === 'unreachable') { text = 'OFF'; color = '#6b7280' }
  }
  try {
    await chrome.action.setBadgeText({ tabId, text })
    await chrome.action.setBadgeBackgroundColor({ tabId, color })
  } catch { /* tab closed */ }
}

export async function refreshActiveBadge() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  if (tab?.id !== undefined) await updateBadge(tab.id)
}
