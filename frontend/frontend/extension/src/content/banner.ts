import { esc, SEV } from '../shared/severity'
import { pumpkinSvg } from '../shared/pumpkin'
import type { Assessment, ToBackground, ToContent } from '../shared/types'

// Injected by the background worker only after an alert on this tab. It reads nothing from the page,
// and it never blocks navigation. The banner lives in a shadow root so site CSS cannot restyle it.

const HOST_ID = 'traceguard-banner-host'

function show(a: Assessment) {
  document.getElementById(HOST_ID)?.remove()
  const high = a.severity === 'HIGH_RISK'
  const m = SEV[a.severity]
  const host = document.createElement('div')
  host.id = HOST_ID
  host.style.cssText = 'all:initial;position:fixed;top:0;left:0;right:0;z-index:2147483647;'
  const root = host.attachShadow({ mode: 'closed' })
  root.innerHTML = `
    <style>
      :host{all:initial}
      .bar{display:flex;align-items:center;gap:14px;padding:10px 16px;font:14px/1.4 system-ui,sans-serif;color:#F3E9C6;
        background:linear-gradient(90deg,#14121C,${high ? '#3a0714' : '#3a1d06'});border-bottom:3px solid ${m.color};
        box-shadow:0 6px 28px ${m.color}88;animation:in .35s ease-out}
      @keyframes in{from{transform:translateY(-100%)}to{transform:none}}
      .txt{flex:1;min-width:0}
      b{color:${m.text};letter-spacing:.04em}
      .host{font-family:ui-monospace,monospace;word-break:break-all}
      button{font:600 13px system-ui,sans-serif;border-radius:8px;padding:7px 12px;cursor:pointer;border:1px solid ${m.color};color:${m.text};background:transparent}
      button.p{background:${m.color};color:#07060B}
      button:focus-visible{outline:2px solid #FF7A1A;outline-offset:2px}
      @media (prefers-reduced-motion:reduce){.bar{animation:none}}
    </style>
    <div class="bar" role="alert">
      <div aria-hidden="true">${pumpkinSvg('threat', 44)}</div>
      <div class="txt">⚠ TraceGuard flagged <span class="host">${esc(a.hostname)}</span> as <b>${m.label}</b>.
        Reason: ${esc(a.reason)} ${a.synthetic ? '<i>(demo data)</i>' : ''}</div>
      <button class="p" id="ev">View evidence</button>
      <button id="x" aria-label="Dismiss warning">Dismiss</button>
    </div>`
  root.getElementById('x')!.addEventListener('click', () => host.remove())
  root.getElementById('ev')!.addEventListener('click', () => {
    const msg: ToBackground = { type: 'OPEN_EVIDENCE', assessment: a }
    void chrome.runtime.sendMessage(msg)
  })
  document.documentElement.appendChild(host)
}

const w = window as unknown as { __tgBannerReady?: boolean }
if (!w.__tgBannerReady) {
  w.__tgBannerReady = true
  chrome.runtime.onMessage.addListener((msg: ToContent) => {
    if (msg.type === 'SHOW_BANNER') show(msg.assessment)
  })
}
