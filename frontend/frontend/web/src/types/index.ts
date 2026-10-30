export type Severity = 'HIGH_RISK' | 'SUSPICIOUS' | 'NEEDS_REVIEW' | 'LOW_OBSERVED_RISK' | 'UNKNOWN'

export const SEVERITIES: Severity[] = ['HIGH_RISK', 'SUSPICIOUS', 'NEEDS_REVIEW', 'LOW_OBSERVED_RISK', 'UNKNOWN']

export interface DailySummary {
  /** ISO date, YYYY-MM-DD */
  date: string
  counts: Record<Severity, number>
}

export interface ConcerningDomain {
  hostname: string
  severity: Severity
  visits: number
  lastSeen: string
  reason: string
}

export interface ReportData {
  from: string
  to: string
  days: DailySummary[]
  topDomains: ConcerningDomain[]
  /** True when the data is synthetic (demo adapter). */
  synthetic: boolean
}
