import type { Severity } from './types'

export const SEV: Record<Severity, { label: string; glyph: string; color: string; text: string; badge: string; badgeColor: string }> = {
  HIGH_RISK: { label: 'HIGH RISK', glyph: '☠', color: '#E5133A', text: '#FF6B86', badge: '!', badgeColor: '#E5133A' },
  SUSPICIOUS: { label: 'SUSPICIOUS', glyph: '👁', color: '#FF7A1A', text: '#FF9A4D', badge: '!', badgeColor: '#FF7A1A' },
  NEEDS_REVIEW: { label: 'NEEDS REVIEW', glyph: '?', color: '#7B3FE4', text: '#B79BFF', badge: '?', badgeColor: '#7B3FE4' },
  LOW_OBSERVED_RISK: { label: 'LOW OBSERVED RISK', glyph: '✓', color: '#39FF88', text: '#39FF88', badge: '✓', badgeColor: '#1d7a45' },
  UNKNOWN: { label: 'UNKNOWN', glyph: '◌', color: '#9AA3B2', text: '#B4BCC9', badge: '?', badgeColor: '#6b7280' },
}

export const esc = (s: string) =>
  s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)
