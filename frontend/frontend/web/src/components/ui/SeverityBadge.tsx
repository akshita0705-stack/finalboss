import type { Severity } from '@/types'
import { SEVERITY_META } from './severity'

/** Always icon + text label, never colour alone. */
export function SeverityBadge({ severity, className = '' }: { severity: Severity; className?: string }) {
  const m = SEVERITY_META[severity]
  const Icon = m.icon
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 font-tech text-xs font-semibold tracking-wide ${className}`}
      style={{ color: m.text, borderColor: `${m.color}99`, background: `${m.color}22`, borderStyle: severity === 'UNKNOWN' ? 'dashed' : 'solid' }}>
      <Icon size={14} aria-hidden />
      {m.label}
    </span>
  )
}
