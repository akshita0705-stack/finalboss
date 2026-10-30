import { DEMO_HOSTS } from '../shared/fixtures'
import { pumpkinSvg, trackPupils, type Mood } from '../shared/pumpkin'
import { esc, SEV } from '../shared/severity'
import { getAlerts, getSettings, getTabStatus } from '../shared/storage'
import type { Assessment, Settings, Severity, TabStatus, ToBackground } from '../shared/types'

const app = document.getElementById('app')!
const send = (m: ToBackground) => chrome.runtime.sendMessage(m)
let stopPupils = () => {}

const badge = (sev: Severity) => {
  const m = SEV[sev]
  return `<span class="badge" style="color:${m.text};border-color:${m.color}99;background:${m.color}22;border-style:${sev === 'UNKNOWN' ? 'dashed' : 'solid'}"><span aria-hidden="true">${m.glyph}</span>${m.label}</span>`
}

function moodAndText(s: Settings, st?: TabStatus): { mood: Mood; text: string } {
  if (!s.consented) return { mood: 'paused', text: 'Consent needed' }
  if (s.paused) return { mood: 'paused', text: 'Paused' }
  if (!s.demoMode && (!s.token || s.backendOk === false)) return { mood: 'offline', text: 'Backend offline' }
  const sev = st?.assessment?.severity
  if (sev === 'HIGH_RISK' || sev === 'SUSPICIOUS') return { mood: 'threat', text: 'Threat detected' }
  return { mood: 'protected', text: 'Protected' }
}

function currentCard(s: Settings, host: string | null, st?: TabStatus): string {
  if (!host) return `<p class="muted">Not a website TraceGuard monitors (browser pages are skipped).</p>`
  const a = st?.assessment
  let body: string
  if (a) {
    body = `<div style="margin:6px 0">${badge(a.severity)}${a.synthetic ? ' <span class="muted">(demo)</span>' : ''}</div>
      <p style="margin:0">${esc(a.reason)}</p>
      <p style="margin:8px 0 0"><a href="#" id="evidence">Open finding in dashboard</a></p>`
  } else if (st?.state === 'unreachable') {
    body = `<div style="margin:6px 0">${badge('UNKNOWN')}</div><p style="margin:0">Not assessed: backend unreachable.</p>`
  } else if (st?.state === 'pending') {
    body = `<p class="muted" style="margin:6px 0 0">The spirits are consulting the evidence…</p>`
  } else {
    body = `<p class="muted" style="margin:6px 0 0">${s.demoMode ? 'Not assessed. Demo mode only knows demo fixtures.' : 'No assessment yet.'} No result is not a safe verdict.</p>`
  }
  return `<h3 style="font-size:12px" class="muted">CURRENT DOMAIN</h3><div class="mono" style="word-break:break-all;margin-top:2px">${esc(host)}</div>${body}`
}

async function render() {
  const s = await getSettings()
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  let host: string | null = null
  try { const u = new URL(tab?.url ?? ''); if (/^https?:$/.test(u.protocol)) host = u.hostname.toLowerCase() } catch { /* no url */ }
  const st = tab?.id !== undefined ? await getTabStatus(tab.id) : undefined
  const alerts = (await getAlerts()).slice(0, 5)
  const { mood, text } = moodAndText(s, st)

  const banners = [
    !s.consented ? `<div class="banner info" role="status">First run: please review what is collected in <a href="#" id="consent">Settings</a> before monitoring starts.</div>` : '',
    s.consented && s.paused ? `<div class="banner info" role="status">Monitoring paused.</div>` : '',
    s.consented && !s.demoMode && (!s.token || s.backendOk === false)
      ? `<div class="banner warn" role="alert">Backend unreachable – not assessed. This is NOT a safe verdict.</div>` : '',
  ].join('')

  app.innerHTML = `
    <header class="hero">
      <div id="mascot">${pumpkinSvg(mood, 96)}</div>
      <div>
        <h1 class="drip" style="font-size:30px;line-height:1">TraceGuard AI</h1>
        <div class="status" style="color:${mood === 'threat' ? '#FF6B86' : mood === 'offline' ? '#B4BCC9' : '#F3E9C6'}">${text}</div>
        ${s.demoMode ? '<span class="badge" style="color:#B79BFF;border-color:#7B3FE499">DEMO MODE</span>' : ''}
      </div>
    </header>
    ${banners}
    <section class="card cobweb" aria-label="Current domain">${currentCard(s, host, st)}</section>
    <section class="card" aria-label="Recent alerts">
      <h3 style="font-size:14px">Recent alerts</h3>
      ${alerts.length ? `<ul class="alerts">${alerts.map((a: Assessment) =>
        `<li><span class="host mono" title="${esc(a.hostname)}">${esc(a.hostname)}</span>${badge(a.severity)}</li>`).join('')}</ul>`
        : '<p class="muted" style="margin:6px 0 0">No alerts yet.</p>'}
    </section>
    <div class="row">
      <button id="pause" ${s.consented ? '' : 'disabled'}>${s.paused ? '▶ Resume' : '⏸ Pause'}</button>
      <button id="dash" class="primary">Open Dashboard</button>
      <button id="settings">Settings</button>
    </div>
    ${s.demoMode ? `<section class="card" aria-label="Demo controller">
      <h3 style="font-size:14px">Demo scenarios <span class="muted">(synthetic)</span></h3>
      <div class="row" style="margin-top:8px">${DEMO_HOSTS.map((h) => `<button data-demo="${esc(h)}" class="mono" style="font-size:11px">${esc(h)}</button>`).join('')}</div>
    </section>` : ''}
    <label class="check muted"><input type="checkbox" id="demoToggle" ${s.demoMode ? 'checked' : ''}/> Demo mode (synthetic events, no backend)</label>
    <p class="muted" style="font-size:11px;margin:0">Cannot inspect encrypted traffic. No result is never a safe verdict.</p>`

  stopPupils(); stopPupils = trackPupils(app)
  const $ = (id: string) => document.getElementById(id)
  $('pause')?.addEventListener('click', () => void send({ type: 'SET_PAUSED', paused: !s.paused }))
  $('dash')?.addEventListener('click', () => void send({ type: 'OPEN_DASHBOARD' }))
  $('settings')?.addEventListener('click', () => void chrome.runtime.openOptionsPage())
  $('consent')?.addEventListener('click', (e) => { e.preventDefault(); void chrome.runtime.openOptionsPage() })
  $('evidence')?.addEventListener('click', (e) => { e.preventDefault(); if (st?.assessment) void send({ type: 'OPEN_EVIDENCE', assessment: st.assessment }) })
  $('demoToggle')?.addEventListener('change', (e) => void chrome.storage.local.set({ settings: { ...s, demoMode: (e.target as HTMLInputElement).checked } }))
  app.querySelectorAll<HTMLButtonElement>('[data-demo]').forEach((b) =>
    b.addEventListener('click', () => void send({ type: 'DEMO', hostname: b.dataset.demo! })))
}

void render()
// Re-render when state changes (settings, alerts, per-tab status).
chrome.storage.onChanged.addListener(() => void render())
