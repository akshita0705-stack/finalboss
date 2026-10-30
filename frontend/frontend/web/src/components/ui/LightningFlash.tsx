import { useEffect } from 'react'
import { useEffectsStore } from '@/store/effects'
import { useReducedEffects } from '@/hooks/useReducedEffects'

/**
 * Subtle rare flash on the dashboard (`ambient`), strong red-white flash when a
 * HIGH RISK alert calls triggerFlash(true). Opacity-only; skipped when effects are reduced.
 */
export function LightningFlash({ ambient = true }: { ambient?: boolean }) {
  const flash = useEffectsStore((s) => s.flash)
  const trigger = useEffectsStore((s) => s.triggerFlash)
  const { reduced } = useReducedEffects()

  useEffect(() => {
    if (!ambient || reduced) return
    let t: number
    const schedule = () => {
      t = window.setTimeout(() => { if (!document.hidden) trigger(false); schedule() }, 25000 + Math.random() * 35000)
    }
    schedule()
    return () => clearTimeout(t)
  }, [ambient, reduced, trigger])

  if (reduced || flash.id === 0) return null
  return (
    <div key={flash.id} aria-hidden className="pointer-events-none fixed inset-0 z-[60] animate-lightning"
      style={{
        background: flash.strong ? 'radial-gradient(circle at 50% 30%, rgba(255,255,255,.55), rgba(229,19,58,.4) 60%, transparent)' : 'rgba(190,210,255,.12)',
        animationDuration: flash.strong ? '1.1s' : '.7s',
      }} />
  )
}
