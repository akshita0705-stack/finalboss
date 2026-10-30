import { useEffect, useRef, useState } from 'react'

export type PumpkinMood = 'monitoring' | 'paused' | 'threat' | 'offline'

const EYE: Record<PumpkinMood, string> = {
  monitoring: '#FFE29A',
  paused: '#FFE29A',
  threat: '#FF2D55',
  offline: '#9AA3B2',
}

const LABEL: Record<PumpkinMood, string> = {
  monitoring: 'Monitoring active',
  paused: 'Monitoring paused',
  threat: 'Threat detected',
  offline: 'Backend offline',
}

/** Jack-o'-lantern whose pupils follow the cursor. Eyes closed = paused, red = threat, grey = offline. */
export function PumpkinScanner({ mood = 'monitoring', size = 140 }: { mood?: PumpkinMood; size?: number }) {
  const ref = useRef<SVGSVGElement>(null)
  const [look, setLook] = useState({ x: 0, y: 0 })

  useEffect(() => {
    if (mood === 'paused' || window.matchMedia('(pointer: coarse)').matches) return
    let raf = 0
    const onMove = (e: MouseEvent) => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const r = ref.current?.getBoundingClientRect()
        if (!r) return
        const dx = e.clientX - (r.left + r.width / 2)
        const dy = e.clientY - (r.top + r.height / 2)
        const len = Math.hypot(dx, dy) || 1
        const k = Math.min(1, len / 200) * 3.2
        setLook({ x: (dx / len) * k, y: (dy / len) * k })
      })
    }
    window.addEventListener('mousemove', onMove)
    return () => { window.removeEventListener('mousemove', onMove); cancelAnimationFrame(raf) }
  }, [mood])

  const eye = EYE[mood]
  const closed = mood === 'paused'
  const glow = mood === 'threat' ? 'rgba(229,19,58,.75)' : mood === 'offline' ? 'rgba(154,163,178,.3)' : 'rgba(255,122,26,.55)'
  const body = mood === 'offline' ? '#6b6f78' : '#FF7A1A'
  const bodyDark = mood === 'offline' ? '#51555d' : '#D9560A'

  return (
    <svg ref={ref} viewBox="0 0 120 110" width={size} height={size * (110 / 120)} role="img" aria-label={LABEL[mood]}
      style={{ filter: `drop-shadow(0 0 18px ${glow})` }}>
      <path d="M58 20q2-12 14-14" stroke="#39FF88" strokeWidth="5" fill="none" strokeLinecap="round" />
      <ellipse cx="32" cy="64" rx="26" ry="38" fill={bodyDark} />
      <ellipse cx="88" cy="64" rx="26" ry="38" fill={bodyDark} />
      <ellipse cx="46" cy="64" rx="30" ry="40" fill={body} />
      <ellipse cx="74" cy="64" rx="30" ry="40" fill={body} />
      <ellipse cx="60" cy="64" rx="22" ry="41" fill={body} />
      {closed ? (
        <g stroke="#07060B" strokeWidth="4" strokeLinecap="round" fill="none">
          <path d="M34 56q8 6 16 0" /><path d="M70 56q8 6 16 0" />
        </g>
      ) : (
        <g>
          <path d="M32 62l10-16 12 16z" fill="#07060B" /><path d="M66 62l12-16 10 16z" fill="#07060B" />
          <circle cx={43 + look.x} cy={57 + look.y} r="4.5" fill={eye} className={mood === 'threat' ? 'animate-flicker' : ''} />
          <circle cx={77 + look.x} cy={57 + look.y} r="4.5" fill={eye} className={mood === 'threat' ? 'animate-flicker' : ''} />
        </g>
      )}
      <path d="M58 70l4 8-4-2z" fill="#07060B" />
      <path d="M30 82l8 8 8-8 8 8 8-8 8 8 8-8 8 8 4-8q-34 14-60 0z" fill="#07060B" />
    </svg>
  )
}
