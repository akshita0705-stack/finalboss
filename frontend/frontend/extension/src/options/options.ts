import { parseExcluded } from '../shared/normalize'
import { esc } from '../shared/severity'
import { getSettings, patchSettings } from '../shared/storage'
import type { ToBackground } from '../shared/types'

const app = document.getElementById('app')!
const send = (m: ToBackground) => chrome.runtime.sendMessage(m)

async function render(note = '') {
  const s = await getSettings()
  app.innerHTML = `
    <header><h1 class="drip" style="font-size:44px;line-height:1">TraceGuard AI</h1>
      <p class="muted" style="margin:4px 0 0">Something is watching. We watch back.</p></header>
    ${note ? `<div class="banner info" role="status">${esc(note)}</div>` : ''}

    <section class="card cobweb" aria-labelledby="c-h">
      <h2 id="c-h">${s.consented ? 'Consent given' : 'Before we start: what TraceGuard collects'}</h2>
      <p><strong>Collected</strong> (only after you agree):</p>
      <ul class="plain"><li>The normalised <em>hostname</em> of sites you visit (for example <span class="mono">example.com</span>).</li>
        <li>An event type, timestamp and a random event id. The previous host, when a redirect is observed.</li></ul>
      <p><strong>Never collected:</strong></p>
      <ul class="plain"><li>Full URLs, paths, query strings or fragments.</li><li>Page content, form values, passwords, cookies, tokens or keystrokes.</li>
        <li>Anything from incognito windows, <span class="mono">chrome://</span>, <span class="mono">file://</span> or extension pages, and excluded domains.</li></ul>
      <p class="muted">Limitations: TraceGuard cannot inspect encrypted traffic, and external domains appear only where reliably observable. A missing result is never a safe verdict.</p>
      <label class="check"><input type="checkbox" id="consent" ${s.consented ? 'checked' : ''}/> I understand and agree to monitoring</label>
    </section>

    <section class="card" aria-labelledby="m-h"><h2 id="m-h">Mode</h2>
      <label class="check"><input type="checkbox" id="demo" ${s.demoMode ? 'checked' : ''}/> Demo mode: synthetic fixtures only, nothing is sent to a backend</label>
      <label class="check"><input type="checkbox" id="effects" ${s.reduceEffects ? 'checked' : ''}/> Reduce spooky effects</label>
    </section>

    <section class="card" aria-labelledby="b-h"><h2 id="b-h">Backend &amp; login</h2>
      <label class="field">Backend URL<input type="url" id="backend" value="${esc(s.backendUrl)}" /></label>
      <label class="field">Dashboard URL<input type="url" id="dashboard" value="${esc(s.dashboardUrl)}" /></label>
      <label class="field">Access token (bearer)<input type="password" id="token" value="${esc(s.token)}" autocomplete="off" /></label>
      <p class="muted" style="margin:6px 0 0">Sign in on the dashboard and paste your extension token here. Status: ${s.backendOk === true ? 'connected' : s.backendOk === false ? 'unreachable' : 'not checked yet'}.</p>
    </section>

    <section class="card" aria-labelledby="x-h"><h2 id="x-h">Privacy controls</h2>
      <label class="field">Excluded domains (one per line, subdomains included)<textarea id="excluded" rows="4" class="mono">${esc(s.excluded.join('\n'))}</textarea></label>
      <label class="field">Keep local alerts for (days)<input type="number" id="retention" min="1" max="365" value="${s.retentionDays}" /></label>
      <div class="check"><button id="grant">Allow in-page warning banner</button><span class="muted">Optional. Asks for site access so a warning can appear on a flagged page only.</span></div>
    </section>

    <div class="row" style="display:flex;gap:8px"><button class="primary" id="save">Save settings</button></div>

    <section class="card" aria-labelledby="d-h" style="border-color:#E5133A66"><h2 id="d-h">Delete my data</h2>
      <p class="muted">Removes the local queue, alerts and settings from this browser and withdraws consent. Type <strong>DELETE</strong> to confirm.</p>
      <div class="check"><input type="text" id="confirm" style="max-width:160px" autocomplete="off" aria-label="Type DELETE to confirm"/><button class="danger" id="delete" disabled>Delete my data</button></div>
    </section>`

  const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T
  $('confirm').addEventListener('input', () => { $<HTMLButtonElement>('delete').disabled = $<HTMLInputElement>('confirm').value !== 'DELETE' })
  $('delete').addEventListener('click', async () => { await send({ type: 'DELETE_ALL' }); setTimeout(() => void render('All local data deleted. Consent withdrawn.'), 300) })
  $('grant').addEventListener('click', async () => {
    const ok = await chrome.permissions.request({ origins: ['<all_urls>'] })
    void render(ok ? 'In-page warning banner enabled.' : 'Site access was not granted. Notifications still work.')
  })
  $('save').addEventListener('click', async () => {
    const backend = $<HTMLInputElement>('backend').value.trim().replace(/\/$/, '')
    try { // ask for access to the configured backend only
      const origin = `${new URL(backend).origin}/*`
      if (!(await chrome.permissions.contains({ origins: [origin] }))) await chrome.permissions.request({ origins: [origin] })
    } catch { /* invalid URL: stored as typed, requests will fail visibly as "backend unreachable" */ }
    await patchSettings({
      consented: $<HTMLInputElement>('consent').checked,
      demoMode: $<HTMLInputElement>('demo').checked,
      reduceEffects: $<HTMLInputElement>('effects').checked,
      backendUrl: backend,
      dashboardUrl: $<HTMLInputElement>('dashboard').value.trim().replace(/\/$/, ''),
      token: $<HTMLInputElement>('token').value.trim(),
      excluded: parseExcluded($<HTMLTextAreaElement>('excluded').value),
      retentionDays: Math.min(365, Math.max(1, Number($<HTMLInputElement>('retention').value) || 30)),
      backendOk: null,
    })
    void send({ type: 'FLUSH' })
    void render('Settings saved.')
  })
}

void render()
