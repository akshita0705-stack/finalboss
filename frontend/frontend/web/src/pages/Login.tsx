import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { authApi, ApiError } from '@/services/api'
import { useAuthStore } from '@/store/auth'
import { DripHeading } from '@/components/ui/DripHeading'
import { HauntedCard } from '@/components/ui/HauntedCard'
import { GlowButton } from '@/components/ui/GlowButton'

type Mode = 'login' | 'register'
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function Login() {
  const [mode, setMode] = useState<Mode>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const token = useAuthStore((s) => s.token)
  const setToken = useAuthStore((s) => s.setToken)
  const nav = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/app'

  if (token) return <Navigate to={from} replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!EMAIL_RE.test(email)) return setError('Enter a valid email address.')
    if (password.length < 8) return setError('Password must be at least 8 characters.')
    setBusy(true)
    try {
      if (mode === 'register') await authApi.register(email, password, name.trim())
      const t = await authApi.login(email, password)
      setToken(t.access_token)
      nav(from, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Try again.')
    } finally {
      setBusy(false)
    }
  }

  const input = 'w-full rounded-lg border border-ghost bg-void px-3 py-2 text-moon outline-none focus:border-pumpkin'

  return (
    <main className="mx-auto flex max-w-md flex-col gap-6 px-6 py-10">
      <DripHeading>{mode === 'login' ? 'Sign in' : 'Create account'}</DripHeading>
      <HauntedCard>
        <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
          {mode === 'register' && (
            <label className="flex flex-col gap-1 text-sm text-fog">Name (optional)
              <input className={input} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
            </label>
          )}
          <label className="flex flex-col gap-1 text-sm text-fog">Email
            <input className={input} type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
          </label>
          <label className="flex flex-col gap-1 text-sm text-fog">Password
            <input className={input} type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required minLength={8} />
          </label>
          {error && <p role="alert" className="text-sm text-[#FF6B86]">{error}</p>}
          <GlowButton type="submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Register & sign in'}</GlowButton>
          <button type="button" className="text-sm text-fog hover:text-moon"
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(null) }}>
            {mode === 'login' ? 'No account? Register' : 'Have an account? Sign in'}
          </button>
        </form>
      </HauntedCard>
    </main>
  )
}
