import type { ConcerningDomain, DailySummary, ReportData, Severity } from '@/types'

/** Small deterministic PRNG so the demo report is stable between renders. */
function mulberry32(seed: number) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const iso = (d: Date) => d.toISOString().slice(0, 10)

// Synthetic only: reserved .invalid / .test / example domains.
const DOMAINS: Omit<ConcerningDomain, 'visits' | 'lastSeen'>[] = [
  { hostname: 'malware-test.traceguard.invalid', severity: 'HIGH_RISK', reason: 'Matched a known-malicious fixture in the threat provider.' },
  { hostname: 'login-verify.example.test', severity: 'HIGH_RISK', reason: 'Credential-style page reached via a 3-hop redirect chain.' },
  { hostname: 'cdn-redirect.example.test', severity: 'SUSPICIOUS', reason: 'Observed redirect through an unrelated host before landing.' },
  { hostname: 'promo-click.traceguard.invalid', severity: 'SUSPICIOUS', reason: 'Repeated redirects to newly seen external domains.' },
  { hostname: 'ads-tracker.example.test', severity: 'NEEDS_REVIEW', reason: 'Third-party tracker contacted; not classified as malicious.' },
  { hostname: 'slow-provider.traceguard.invalid', severity: 'UNKNOWN', reason: 'Threat provider timed out; assessment unavailable.' },
]

/** Builds a synthetic report ending today. `daysBack` is the window length. */
export function buildDemoReport(daysBack: number): ReportData {
  const rand = mulberry32(1337)
  const today = new Date()
  const days: DailySummary[] = []
  for (let i = daysBack - 1; i >= 0; i--) {
    const d = new Date(today); d.setDate(today.getDate() - i)
    const spike = rand() < 0.12 ? 3 : 0
    const counts: Record<Severity, number> = {
      HIGH_RISK: Math.floor(rand() * 2) + (spike ? 2 : 0),
      SUSPICIOUS: Math.floor(rand() * 4) + spike,
      NEEDS_REVIEW: Math.floor(rand() * 5),
      LOW_OBSERVED_RISK: 30 + Math.floor(rand() * 40),
      UNKNOWN: Math.floor(rand() * 4),
    }
    days.push({ date: iso(d), counts })
  }
  const lastSeen = days[days.length - 1].date
  const topDomains = DOMAINS.map((d) => ({ ...d, visits: 2 + Math.floor(rand() * 14), lastSeen }))
  return { from: days[0].date, to: lastSeen, days, topDomains, synthetic: true }
}

export function loadReport(daysBack: number): Promise<ReportData> {
  return new Promise((resolve) => setTimeout(() => resolve(buildDemoReport(daysBack)), 700))
}
