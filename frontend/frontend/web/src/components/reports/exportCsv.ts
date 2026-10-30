import { SEVERITIES, type ReportData } from '@/types'

const esc = (v: string | number) => {
  const s = String(v)
  // Quote fields and neutralise spreadsheet formula injection.
  const safe = /^[=+\-@]/.test(s) ? `'${s}` : s
  return /[",\n]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe
}

export function reportToCsv(r: ReportData): string {
  const source = r.synthetic ? 'synthetic-demo' : 'live'
  const lines = [['date', ...SEVERITIES.map((s) => s.toLowerCase()), 'source'].join(',')]
  for (const d of r.days) lines.push([d.date, ...SEVERITIES.map((s) => d.counts[s]), source].join(','))
  lines.push('', ['hostname', 'severity', 'visits', 'last_seen', 'reason', 'source'].join(','))
  for (const t of r.topDomains) lines.push([t.hostname, t.severity, t.visits, t.lastSeen, t.reason, source].map(esc).join(','))
  return lines.join('\n')
}

export function downloadCsv(r: ReportData) {
  const url = URL.createObjectURL(new Blob([reportToCsv(r)], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `traceguard-report_${r.from}_${r.to}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
