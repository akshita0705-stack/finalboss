export type Severity = 'HIGH_RISK' | 'SUSPICIOUS' | 'NEEDS_REVIEW' | 'LOW_OBSERVED_RISK' | 'UNKNOWN'

export interface Assessment {
  hostname: string
  severity: Severity
  reason: string
  findingId?: string
  redirects?: string[]
  /** epoch ms */
  at: number
  synthetic: boolean
}

/** The only data ever sent to the backend. No URLs, paths, queries, cookies, form values or page content. */
export interface NavEvent {
  event_id: string
  hostname: string
  event_type: 'navigation' | 'error'
  timestamp: string
  redirect_from_host?: string
  observed_external_domains?: string[]
}

export interface Settings {
  consented: boolean
  paused: boolean
  demoMode: boolean
  backendUrl: string
  dashboardUrl: string
  token: string
  excluded: string[]
  retentionDays: number
  reduceEffects: boolean
  notifySeverities: Severity[]
  /** null = not yet known */
  backendOk: boolean | null
}

export type TabState = 'assessed' | 'pending' | 'unreachable' | 'skipped'

export interface TabStatus {
  state: TabState
  assessment?: Assessment
}

export interface QueueItem {
  event: NavEvent
  tabId: number
  attempts: number
  nextAt: number
}

/** popup/options/content -> background */
export type ToBackground =
  | { type: 'SET_PAUSED'; paused: boolean }
  | { type: 'DEMO'; hostname: string }
  | { type: 'OPEN_EVIDENCE'; assessment: Assessment }
  | { type: 'OPEN_DASHBOARD' }
  | { type: 'DELETE_ALL' }
  | { type: 'FLUSH' }

/** background -> content */
export type ToContent = { type: 'SHOW_BANNER'; assessment: Assessment }
