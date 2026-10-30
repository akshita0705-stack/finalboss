import { useMemo } from 'react'

/** ~70 twinkling stars; only opacity animates. */
export function StarField({ count = 70 }: { count?: number }) {
  const stars = useMemo(
    () => Array.from({ length: count }, () => ({
      x: Math.random() * 100, y: Math.random() * 70,
      s: Math.random() < 0.15 ? 3 : 2, d: Math.random() * 4, t: 2 + Math.random() * 4,
    })),
    [count],
  )
  return (
    <div className="atmos absolute inset-0" aria-hidden>
      {stars.map((s, i) => (
        <span key={i} className="absolute rounded-full bg-moon animate-twinkle"
          style={{ left: `${s.x}%`, top: `${s.y}%`, width: s.s, height: s.s, animationDelay: `${s.d}s`, animationDuration: `${s.t}s` }} />
      ))}
    </div>
  )
}
