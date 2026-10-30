import { Link } from 'react-router-dom'
import { useEffectsStore } from '@/store/effects'

export default function Home() {
  const flash = useEffectsStore((s) => s.triggerFlash)
  return (
    <section className="mx-auto mt-16 max-w-2xl px-4 text-center">
      <h1 className="drip-text neon-flicker text-6xl sm:text-7xl">TraceGuard AI</h1>
      <p className="mt-4 font-tech text-xl text-moon">Something is watching. We watch back.</p>
      <p className="mt-2 text-fog">Landing page comes in a later step. The Reports page is ready.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link to="/app/reports" className="rounded-lg bg-pumpkin px-4 py-2 font-tech font-semibold text-void hover:shadow-pumpkin">Open Reports</Link>
        <button onClick={() => flash(false)} className="rounded-lg border border-pumpkin px-4 py-2 text-pumpkin hover:shadow-pumpkin">Test ambient flash</button>
        <button onClick={() => flash(true)} className="rounded-lg border border-blood px-4 py-2 text-[#FF6B86] hover:shadow-blood">Test HIGH RISK flash</button>
      </div>
    </section>
  )
}
