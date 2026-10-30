import type { Severity } from '@/types'

export interface Assessment {
  hostname: string
  severity: Severity
  reason: string
  /** Redirect hops actually observed, if any. */
  redirects: string[]
  synthetic: true
}

/** Strip scheme, credentials, path, query, fragment and port; lower-case. Only the hostname is ever kept. */
export function normalizeHost(input: string): string {
  const s = input.trim().toLowerCase().replace(/^[a-z][a-z0-9+.-]*:\/\//, '')
  return s.split(/[/?#]/)[0].replace(/^.*@/, '').replace(/:\d+$/, '')
}

// Synthetic fixtures only: reserved .invalid / .test / example domains.
const FIXTURES: Record<string, Omit<Assessment, 'hostname' | 'synthetic'>> = {
  'malware-test.traceguard.invalid': {
    severity: 'HIGH_RISK', redirects: [],
    reason: 'Matched a known-malicious test fixture in the threat provider.',
  },
  'login-verify.example.test': {
    severity: 'SUSPICIOUS', redirects: ['short-link.example.test', 'cdn-redirect.example.test', 'login-verify.example.test'],
    reason: 'Reached through a 3-hop redirect chain and asks for credentials.',
  },
  'ads-tracker.example.test': {
    severity: 'NEEDS_REVIEW', redirects: [],
    reason: 'Third-party tracker observed. Not classified as malicious.',
  },
  'news.example.test': {
    severity: 'LOW_OBSERVED_RISK', redirects: [],
    reason: 'No significant issue found in the signals checked.',
  },
}

export function assess(rawInput: string): Promise<Assessment> {
  const hostname = normalizeHost(rawInput)
  const hit = FIXTURES[hostname]
  const result: Assessment = hit
    ? { hostname, synthetic: true, ...hit }
    // Unknown host: never imply safety when nothing was assessed.
    : { hostname, synthetic: true, severity: 'UNKNOWN', redirects: [], reason: 'Assessment unavailable. This is NOT a safe verdict.' }
  return new Promise((resolve) => setTimeout(() => resolve(result), 900))
}

export const PRESETS = Object.keys(FIXTURES)
