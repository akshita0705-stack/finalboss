import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { useSyncEffectFlags } from '@/hooks/useReducedEffects'
import Home from '@/pages/Home'
import { RequireAuth } from '@/components/auth/RequireAuth'

const Reports = lazy(() => import('@/pages/Reports'))
const SiteCheck = lazy(() => import('@/pages/SiteCheck'))
const Login = lazy(() => import('@/pages/Login'))
const Overview = lazy(() => import('@/pages/Overview'))

export default function App() {
  useSyncEffectFlags()
  return (
    <BrowserRouter>
      <Suspense fallback={<p className="p-8 text-fog">Loading…</p>}>
        <Routes>
          <Route element={<AppShell />}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route element={<RequireAuth />}>
              <Route path="/app" element={<Overview />} />
              <Route path="/app/reports" element={<Reports />} />
              <Route path="/app/site-check" element={<SiteCheck />} />
            </Route>
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
