import { useCallback, useState, type FormEvent } from 'react'
import { motion } from 'framer-motion'
import { Globe, Lock } from 'lucide-react'
import { assess, normalizeHost, PRESETS, type Assessment } from '@/services/demo/assess'
import { DripHeading } from '@/components/ui/DripHeading'
import { HauntedCard } from '@/components/ui/HauntedCard'
import { GlowButton } from '@/components/ui/GlowButton'
import { PumpkinScanner, type PumpkinMood } from '@/components/ui/PumpkinScanner'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { WarningPopup } from '@/components/ui/WarningPopup'

type Phase = 'idle' | 'scanning' | 'done'

export default function SiteCheck() {
  const [input, setInput] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<Assessment | null>(null)
  const [popup, setPopup] = useState<Assessment | null>(null)
  const [proceeded, setProceeded] = useState(false)

  const visit = useCallback(async (raw: string) => {
    if (!normalizeHost(raw)) return
    setPhase('scanning'); setResult(null); setProceeded(false)
    const a = await assess(raw)
    setResult(a); setPhase('done')
    if (a.severity === 'HIGH_RISK' || a.severity === 'SUSPICIOUS') setPopup(a)
  }, [])

  const onSubmit = (e: FormEvent) => { e.preventDefault(); void visit(input) }
  const goBack = useCallback(() => { setPopup(null); setResult(null); setPhase('idle'); setInput('') }, [])
  const proceed = useCallback(() => { setPopup(null); setProceeded(true) }, [])

  const mood: PumpkinMood = phase === 'done' && result && ['HIGH_RISK', 'SUSPICIOUS'].includes(result.severity) ? 'threat' : 'monitoring'

  return (
    <motion.main initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-3xl px-4 pb-24 pt-6 sm:px-6">
      <p className="mb-4 inline-block rounded border border-witch/60 bg-witch/10 px-2 py-1 font-tech text-xs tracking-widest text-[#B79BFF]">
        DEMO MODE – SYNTHETIC DATA · NO REAL SITE IS OPENED
      </p>
      <div className="flex items-center gap-4">
        <PumpkinScanner mood={mood} size={96} />
        <div>
          <DripHeading className="text-4xl sm:text-5xl">Site Check</DripHeading>
          <p className="font-tech text-moon">Open a site. See the warning.</p>
        </div>
      </div>

      <HauntedCard className="mt-6">
        <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row" aria-label="Open a website">
          <label htmlFor="url" className="sr-only">Website address</label>
          <div className="flex flex-1 items-center gap-2 rounded-lg border border-ghost bg-surface-2 px-3">
            <Lock size={14} className="text-fog" aria-hidden />
            <input id="url" value={input} onChange={(e) => setInput(e.target.value)} placeholder="malware-test.traceguard.invalid"
              autoComplete="off" spellCheck={false}
              className="w-full bg-transparent py-2 font-mono text-sm text-moon placeholder:text-fog/60 focus:outline-none" />
          </div>
          <GlowButton type="submit" disabled={phase === 'scanning' || !input.trim()}><Globe size={16} aria-hidden />Open site</GlowButton>
        </form>

        <div className="mt-4">
          <p className="mb-2 text-xs text-fog">Try a demo scenario:</p>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button key={p} onClick={() => { setInput(p); void visit(p) }} disabled={phase === 'scanning'}
                className="rounded-md border border-ghost bg-surface-2 px-2 py-1 font-mono text-xs text-moon transition hover:border-pumpkin disabled:opacity-50">
                {p}
              </button>
            ))}
          </div>
        </div>
      </HauntedCard>

      <div className="mt-6" aria-live="polite">
        {phase === 'scanning' && (
          <HauntedCard className="flex items-center gap-4">
            <PumpkinScanner mood="monitoring" size={70} />
            <p className="text-fog">The pumpkin is analysing the domain…</p>
          </HauntedCard>
        )}
        {phase === 'done' && result && !popup && (
          <HauntedCard>
            <div className="flex flex-wrap items-center gap-3">
              <SeverityBadge severity={result.severity} />
              <span className="font-mono text-moon">{result.hostname}</span>
            </div>
            <p className="mt-2 text-sm text-fog">{result.reason}</p>
            {proceeded && <p className="mt-2 text-xs text-[#FF9A4D]">You chose to continue despite the warning. Nothing was blocked.</p>}
          </HauntedCard>
        )}
      </div>

      <WarningPopup assessment={popup} onBack={goBack} onProceed={proceed} />
    </motion.main>
  )
}
