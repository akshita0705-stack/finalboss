import { create } from 'zustand'

interface EffectsState {
  reduceEffects: boolean
  sound: boolean
  /** Bumped to trigger a lightning flash; `strong` is used for HIGH RISK alerts. */
  flash: { id: number; strong: boolean }
  setReduce: (v: boolean) => void
  setSound: (v: boolean) => void
  triggerFlash: (strong?: boolean) => void
}

const read = (k: string, d: boolean) => {
  try { const v = localStorage.getItem(k); return v === null ? d : v === '1' } catch { return d }
}
const write = (k: string, v: boolean) => { try { localStorage.setItem(k, v ? '1' : '0') } catch { /* storage unavailable */ } }

export const useEffectsStore = create<EffectsState>((set) => ({
  reduceEffects: read('tg.reduce', false),
  sound: read('tg.sound', false), // OFF by default
  flash: { id: 0, strong: false },
  setReduce: (v) => { write('tg.reduce', v); set({ reduceEffects: v }) },
  setSound: (v) => { write('tg.sound', v); set({ sound: v }) },
  triggerFlash: (strong = false) => set((s) => ({ flash: { id: s.flash.id + 1, strong } })),
}))
