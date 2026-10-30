import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { DEMO_MODE } from '@/services/api'

/** Demo mode (VITE_DEMO_MODE=true) skips login and uses synthetic data only. */
export function RequireAuth() {
  const token = useAuthStore((s) => s.token)
  const loc = useLocation()
  if (!DEMO_MODE && !token) return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  return <Outlet />
}
