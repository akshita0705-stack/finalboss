import type { DailySummary, Severity } from '@/types'

export interface RecentFinding {
  id: string
  domain: string
  severity: string
  status_label: Severity
  risk_score: number
  status: string
  explanation: string
  created_at: string
}

export interface RecentEvent {
  id: string
  domain: string
  event_type: string
  status_label: Severity
  created_at: string
}

export interface HealthItem { ok: boolean; label: string; detail: string }

export interface DashboardSummary {
  installations_linked: number
  last_event_at: string | null
  total_events: number
  total_findings: number
  open_findings: number
  status_counts: Record<Severity, number>
  trend: DailySummary[]
  recent_findings: RecentFinding[]
  recent_events: RecentEvent[]
  health: { backend: HealthItem; graph: HealthItem; threat_provider: HealthItem }
  limitations: string
}
