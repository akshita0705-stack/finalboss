import { SEVERITIES, type Severity } from '@/types'
import { SEVERITY_META } from '@/components/ui/severity'
import { SeverityBadge } from '@/components/ui/SeverityBadge'

/** Horizontal bars, one per severity, each labelled directly (icon + text + count). */
export function Breakdown({ totals }: { totals: Record<Severity, number> }) {
  const max = Math.max(1, ...SEVERITIES.map((s) => totals[s]))
  return (
    <ul className="space-y-3">
      {SEVERITIES.map((s) => (
        <li key={s} className="grid grid-cols-[11rem_1fr_3.5rem] items-center gap-3">
          <SeverityBadge severity={s} />
          <div className="h-3 rounded-r bg-surface-2" aria-hidden>
            <div className="h-3 rounded-r transition-[width] duration-500"
              style={{ width: `${(totals[s] / max) * 100}%`, background: SEVERITY_META[s].color, opacity: s === 'UNKNOWN' ? 0.6 : 1 }} />
          </div>
          <span className="text-right font-mono text-sm text-moon">{totals[s]}</span>
        </li>
      ))}
    </ul>
  )
}
