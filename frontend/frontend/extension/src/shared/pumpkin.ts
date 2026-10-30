export type Mood = 'protected' | 'paused' | 'threat' | 'offline'

const EYE: Record<Mood, string> = { protected: '#FFE29A', paused: '#FFE29A', threat: '#FF2D55', offline: '#9AA3B2' }

/** Pumpkin mascot markup. Pupils have ids pg-l / pg-r so the popup can move them toward the cursor. */
export function pumpkinSvg(mood: Mood, width = 120): string {
  const body = mood === 'offline' ? '#6b6f78' : '#FF7A1A'
  const dark = mood === 'offline' ? '#51555d' : '#D9560A'
  const glow = mood === 'threat' ? 'rgba(229,19,58,.75)' : mood === 'offline' ? 'rgba(154,163,178,.3)' : 'rgba(255,122,26,.55)'
  const eyes = mood === 'paused'
    ? '<g stroke="#07060B" stroke-width="4" stroke-linecap="round" fill="none"><path d="M34 56q8 6 16 0"/><path d="M70 56q8 6 16 0"/></g>'
    : `<path d="M32 62l10-16 12 16z" fill="#07060B"/><path d="M66 62l12-16 10 16z" fill="#07060B"/>
       <circle id="pg-l" cx="43" cy="57" r="4.5" fill="${EYE[mood]}"/><circle id="pg-r" cx="77" cy="57" r="4.5" fill="${EYE[mood]}"/>`
  return `<svg viewBox="0 0 120 110" width="${width}" height="${width * 110 / 120}" role="img" aria-label="TraceGuard mascot" style="filter:drop-shadow(0 0 16px ${glow})">
    <path d="M58 20q2-12 14-14" stroke="#39FF88" stroke-width="5" fill="none" stroke-linecap="round"/>
    <ellipse cx="32" cy="64" rx="26" ry="38" fill="${dark}"/><ellipse cx="88" cy="64" rx="26" ry="38" fill="${dark}"/>
    <ellipse cx="46" cy="64" rx="30" ry="40" fill="${body}"/><ellipse cx="74" cy="64" rx="30" ry="40" fill="${body}"/><ellipse cx="60" cy="64" rx="22" ry="41" fill="${body}"/>
    ${eyes}
    <path d="M58 70l4 8-4-2z" fill="#07060B"/>
    <path d="M30 82l8 8 8-8 8 8 8-8 8 8 8-8 8 8 4-8q-34 14-60 0z" fill="#07060B"/>
  </svg>`
}

/** Makes the pupils follow the mouse. Returns a cleanup function. */
export function trackPupils(root: ParentNode): () => void {
  const l = root.querySelector<SVGElement>('#pg-l'), r = root.querySelector<SVGElement>('#pg-r')
  if (!l || !r) return () => {}
  const svg = l.ownerSVGElement!
  const move = (e: MouseEvent) => {
    const b = svg.getBoundingClientRect()
    const dx = e.clientX - (b.left + b.width / 2), dy = e.clientY - (b.top + b.height / 2)
    const len = Math.hypot(dx, dy) || 1, k = Math.min(1, len / 150) * 3.2
    const t = `translate(${(dx / len) * k}px, ${(dy / len) * k}px)`
    l.style.transform = t; r.style.transform = t
  }
  window.addEventListener('mousemove', move)
  return () => window.removeEventListener('mousemove', move)
}
