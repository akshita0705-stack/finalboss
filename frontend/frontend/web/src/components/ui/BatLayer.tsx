import { useMemo } from 'react'

function Bat() {
  return (
    <svg viewBox="0 0 64 32" className="h-full w-full" fill="#07060B">
      <g className="animate-flap" style={{ transformBox: 'fill-box', transformOrigin: 'center' }}>
        <path d="M32 10c-2 0-3 2-4 4-3-4-8-6-14-5 3 2 4 5 4 8-4-1-8 0-12 3 5 0 8 2 10 5 2-3 5-4 8-3 2 3 4 5 8 5s6-2 8-5c3-1 6 0 8 3 2-3 5-5 10-5-4-3-8-4-12-3 0-3 1-6 4-8-6-1-11 1-14 5-1-2-2-4-4-4z" />
      </g>
    </svg>
  )
}

const KEYFRAMES = `@keyframes bat-ltr{from{transform:translate3d(-12vw,0,0)}50%{transform:translate3d(50vw,var(--rise),0)}to{transform:translate3d(112vw,0,0)}}
@keyframes bat-rtl{from{transform:translate3d(112vw,0,0)}50%{transform:translate3d(50vw,var(--rise),0)}to{transform:translate3d(-12vw,0,0)}}`

/** 5-8 bats crossing the sky. Paths are randomised per mount; transform-only CSS animation. */
export function BatLayer({ count = 6 }: { count?: number }) {
  const bats = useMemo(
    () => Array.from({ length: count }, (_, i) => ({
      id: i, top: 5 + Math.random() * 45, size: 22 + Math.random() * 34,
      dur: 14 + Math.random() * 18, delay: -Math.random() * 30, rise: (Math.random() - 0.5) * 140, rtl: Math.random() < 0.5,
    })),
    [count],
  )
  return (
    <div className="atmos atmos-heavy absolute inset-0 overflow-hidden" aria-hidden>
      <style>{KEYFRAMES}</style>
      {bats.map((b) => (
        <div key={b.id} className="absolute left-0 will-change-transform"
          style={{
            top: `${b.top}%`, width: b.size, height: b.size / 2, ['--rise' as string]: `${b.rise}px`,
            animation: `${b.rtl ? 'bat-rtl' : 'bat-ltr'} ${b.dur}s linear ${b.delay}s infinite`, opacity: 0.85,
          }}>
          <Bat />
        </div>
      ))}
    </div>
  )
}
