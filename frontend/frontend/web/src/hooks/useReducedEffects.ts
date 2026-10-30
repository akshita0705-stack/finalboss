import { useEffect, useState } from 'react'
import { useEffectsStore } from '@/store/effects'

/** True when the OS asks for reduced motion, regardless of the in-app toggle. */
function usePrefersReducedMotion() {
  const [m, setM] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches)
  useEffect(() => {
    const q = window.matchMedia('(prefers-reduced-motion: reduce)')
    const h = () => setM(q.matches)
    q.addEventListener('change', h)
    return () => q.removeEventListener('change', h)
  }, [])
  return m
}

/** Single source of truth: heavy spooky effects are off if OS or user says so. */
export function useReducedEffects() {
  const os = usePrefersReducedMotion()
  const user = useEffectsStore((s) => s.reduceEffects)
  const setReduce = useEffectsStore((s) => s.setReduce)
  return { reduced: os || user, osForced: os, toggle: () => setReduce(!user) }
}

/** Mirrors state onto <html> so CSS can pause/disable layers without re-rendering them. */
export function useSyncEffectFlags() {
  const { reduced } = useReducedEffects()
  useEffect(() => { document.documentElement.dataset.reduce = String(reduced) }, [reduced])
  useEffect(() => {
    const h = () => { document.documentElement.dataset.hidden = String(document.hidden) }
    h()
    document.addEventListener('visibilitychange', h)
    return () => document.removeEventListener('visibilitychange', h)
  }, [])
}
