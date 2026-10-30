import { CircleDashed, CircleHelp, Ghost, ShieldCheck, Skull, type LucideIcon } from 'lucide-react'
import type { Severity } from '@/types'

interface SeverityMeta {
  label: string
  icon: LucideIcon
  /** Brand colour for chart marks and borders. */
  color: string
  /** Lighter tint used for text so it stays >= 4.5:1 on the dark surfaces. */
  text: string
}

export const SEVERITY_META: Record<Severity, SeverityMeta> = {
  HIGH_RISK: { label: 'HIGH RISK', icon: Skull, color: '#E5133A', text: '#FF6B86' },
  SUSPICIOUS: { label: 'SUSPICIOUS', icon: Ghost, color: '#FF7A1A', text: '#FF9A4D' },
  NEEDS_REVIEW: { label: 'NEEDS REVIEW', icon: CircleHelp, color: '#7B3FE4', text: '#B79BFF' },
  LOW_OBSERVED_RISK: { label: 'LOW OBSERVED RISK', icon: ShieldCheck, color: '#39FF88', text: '#39FF88' },
  UNKNOWN: { label: 'UNKNOWN', icon: CircleDashed, color: '#9AA3B2', text: '#B4BCC9' },
}
