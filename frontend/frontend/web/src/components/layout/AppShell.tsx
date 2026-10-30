import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { Atmosphere } from '@/components/ui/Atmosphere'
import { GlitchText } from '@/components/ui/GlitchText'
import { useReducedEffects } from '@/hooks/useReducedEffects'
import { Ghost, LogOut, Sparkles } from 'lucide-react'
import { useAuthStore } from '@/store/auth'

/** Temporary top-nav layout; the sidebar/top bar arrives with the app shell step. */
export function AppShell() {
  const { reduced, osForced, toggle } = useReducedEffects()
  const { pathname } = useLocation()
  const token = useAuthStore((s) => s.token)
  const logout = useAuthStore((s) => s.logout)
  return (
    <div className="relative min-h-screen">
      <Atmosphere variant={pathname === '/' ? 'hero' : 'dashboard'} />
      <header className="print-hide flex items-center justify-between gap-3 px-6 py-4">
        <Link to="/"><GlitchText as="span" className="font-tech text-xl font-bold tracking-wide text-moon">TraceGuard AI</GlitchText></Link>
        <nav aria-label="Main" className="flex gap-4 font-tech text-sm">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'text-pumpkin' : 'text-fog hover:text-moon')}>Home</NavLink>
          <NavLink to="/app" end className={({ isActive }) => (isActive ? 'text-pumpkin' : 'text-fog hover:text-moon')}>Overview</NavLink>
          <NavLink to="/app/reports" className={({ isActive }) => (isActive ? 'text-pumpkin' : 'text-fog hover:text-moon')}>Reports</NavLink>
          <NavLink to="/app/site-check" className={({ isActive }) => (isActive ? 'text-pumpkin' : 'text-fog hover:text-moon')}>Site Check</NavLink>
        </nav>
        {token && (<button onClick={logout} className="inline-flex items-center gap-2 text-sm text-fog hover:text-moon"><LogOut size={16} aria-hidden /> Sign out</button>)}
        <button onClick={toggle} disabled={osForced} aria-pressed={reduced}
          className="inline-flex items-center gap-2 rounded-lg border border-ghost bg-surface/80 px-3 py-1.5 text-sm text-moon transition hover:border-pumpkin hover:shadow-pumpkin disabled:opacity-60">
          {reduced ? <Ghost size={16} aria-hidden /> : <Sparkles size={16} aria-hidden />}
          {osForced ? 'Effects off (OS setting)' : reduced ? 'Spooky effects: off' : 'Spooky effects: on'}
        </button>
      </header>
      <Outlet />
    </div>
  )
}
