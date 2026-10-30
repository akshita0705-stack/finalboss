import { useMemo } from 'react'

/** Capped orange ember particles rising from the bottom. */
export function Embers({ count = 18 }: { count?: number }) {
  const items = useMemo(
    () => Array.from({ length: Math.min(count, 24) }, () => ({
      x: Math.random() * 100, s: 2 + Math.random() * 3, d: -Math.random() * 14, t: 9 + Math.random() * 9, dx: (Math.random() - 0.5) * 120,
    })),
    [count],
  )
  return (
    <div className="atmos atmos-heavy absolute inset-0 overflow-hidden" aria-hidden>
      {items.map((e, i) => (
        <span key={i} className="absolute bottom-0 rounded-full bg-pumpkin-glow animate-ember will-change-transform"
          style={{
            left: `${e.x}%`, width: e.s, height: e.s, animationDelay: `${e.d}s`, animationDuration: `${e.t}s`,
            ['--dx' as string]: `${e.dx}px`, boxShadow: '0 0 8px 2px rgba(255,122,26,.7)',
          }} />
      ))}
    </div>
  )
}
