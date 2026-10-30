import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Eye, ShieldAlert } from 'lucide-react'
import type { Assessment } from '@/services/demo/assess'
import { useEffectsStore } from '@/store/effects'
import { PumpkinScanner } from './PumpkinScanner'
import { DripHeading } from './DripHeading'
import { GlowButton } from './GlowButton'
import { SeverityBadge } from './SeverityBadge'

interface Props {
  assessment: Assessment | null
  onBack: () => void
  onProceed: () => void
}

/** Full-screen horror warning for HIGH RISK / SUSPICIOUS sites. Never blocks: the user can always proceed. */
export function WarningPopup({ assessment, onBack, onProceed }: Props) {
  const flash = useEffectsStore((s) => s.triggerFlash)
  const backRef = useRef<HTMLButtonElement>(null)
  const [showEvidence, setShowEvidence] = useState(false)
  const open = !!assessment
  const high = assessment?.severity === 'HIGH_RISK'

  useEffect(() => {
    if (!open) return
    setShowEvidence(false)
    flash(high)
    backRef.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onBack() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, high, flash, onBack])

  return (
    <AnimatePresence>
      {assessment && (
        <motion.div className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-void/85 p-4 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <motion.div role="alertdialog" aria-modal="true" aria-labelledby="warn-title" aria-describedby="warn-desc"
            initial={{ scale: 0.85, y: 30 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.9, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            className={`${high ? 'shake border-blood shadow-blood' : 'border-pumpkin shadow-pumpkin'} alert-pulse relative w-full max-w-lg rounded-2xl border-2 bg-surface p-6 text-center`}>
            <div className="flex justify-center"><PumpkinScanner mood="threat" size={150} /></div>
            <div id="warn-title">
              <DripHeading as="p" tone={high ? 'blood' : 'pumpkin'} className="text-5xl sm:text-6xl">
                {high ? 'DANGER!' : 'BEWARE!'}
              </DripHeading>
            </div>
            <div className="mt-1 flex justify-center"><SeverityBadge severity={assessment.severity} /></div>
            <p className="mt-3 font-mono text-lg text-moon break-all">{assessment.hostname}</p>
            <p id="warn-desc" className="mt-2 text-sm text-fog">
              {assessment.reason} TraceGuard is only warning you. It has not blocked anything.
            </p>

            {showEvidence && (
              <div className="mt-4 rounded-lg border border-ghost bg-surface-2 p-3 text-left text-sm">
                <p className="font-tech text-moon">Evidence</p>
                <p className="mt-1 text-fog">{assessment.reason}</p>
                {assessment.redirects.length > 0 && (
                  <ol className="mt-2 space-y-1 font-mono text-xs text-moon">
                    {assessment.redirects.map((h, i) => <li key={h}>{i + 1}. {h}</li>)}
                  </ol>
                )}
                <p className="mt-2 text-xs text-fog">Limitation: demo data. Encrypted traffic is not inspected.</p>
              </div>
            )}

            <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-center">
              <button ref={backRef} onClick={onBack}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-pumpkin px-4 py-2 font-tech text-sm font-semibold text-void transition hover:bg-pumpkin-glow hover:shadow-pumpkin">
                <ShieldAlert size={16} aria-hidden />Take me back to safety
              </button>
              <GlowButton variant="outline" onClick={() => setShowEvidence((v) => !v)} aria-expanded={showEvidence}>
                <Eye size={16} aria-hidden />{showEvidence ? 'Hide evidence' : 'View evidence'}
              </GlowButton>
            </div>
            <button onClick={onProceed} className="mt-3 inline-flex items-center gap-1 text-xs text-fog underline-offset-2 hover:text-moon hover:underline">
              I understand the risk, continue anyway <ArrowRight size={12} aria-hidden />
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
