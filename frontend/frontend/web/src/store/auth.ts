import { create } from 'zustand'

const KEY = 'tg.token'
const read = () => { try { return sessionStorage.getItem(KEY) } catch { return null } }
const write = (v: string | null) => {
  try { v ? sessionStorage.setItem(KEY, v) : sessionStorage.removeItem(KEY) } catch { /* storage unavailable */ }
}

interface AuthState {
  token: string | null
  setToken: (t: string) => void
  logout: () => void
}

/** Token lives in sessionStorage (cleared when the tab closes), never in localStorage. */
export const useAuthStore = create<AuthState>((set) => ({
  token: read(),
  setToken: (t) => { write(t); set({ token: t }) },
  logout: () => { write(null); set({ token: null }) },
}))
