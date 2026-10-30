import type { Assessment } from './types'

// Synthetic fixtures only: reserved .invalid / .test / example domains. Never real malicious sites.
type Fixture = Pick<Assessment, 'severity' | 'reason' | 'redirects'>

export const FIXTURES: Record<string, Fixture> = {
  'malware-test.traceguard.invalid': { severity: 'HIGH_RISK', reason: 'Matched a known-malicious test fixture in the threat provider.' },
  'login-verify.example.test': {
    severity: 'SUSPICIOUS', reason: 'Reached through a 3-hop redirect chain and asks for credentials.',
    redirects: ['short-link.example.test', 'cdn-redirect.example.test', 'login-verify.example.test'],
  },
  'ads-tracker.example.test': { severity: 'NEEDS_REVIEW', reason: 'Third-party tracker observed. Not classified as malicious.' },
  'news.example.test': { severity: 'LOW_OBSERVED_RISK', reason: 'No significant issue found in the signals checked.' },
}

export const DEMO_HOSTS = Object.keys(FIXTURES)

/** Demo mode only knows the fixtures; anything else is "not assessed", never "safe". */
export function demoAssess(hostname: string): Assessment | null {
  const f = FIXTURES[hostname]
  return f ? { hostname, ...f, at: Date.now(), synthetic: true } : null
}
