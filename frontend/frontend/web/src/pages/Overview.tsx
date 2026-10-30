import { useCallback, useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { ApiError, DEMO_MODE, dashboardApi } from '@/services/api'
import { SEVERITIES, type Severity } from '@/types'
import type { DashboardSummary } from '@/types/dashboard'
import { DripHeading } from '@/components/ui/DripHeading'
import { HauntedCard } from '@/components/ui/HauntedCard'
import { GlowButton } from '@/components/ui/GlowButton'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { TrendChart } from '@/components/reports/TrendChart'
import { HealthPanel } from '@/components/dashboard/HealthPanel'
import { LinkExtension } from '@/components/dashboard/LinkExtension'

const DAYS = 7
const POLL_MS = 15000
const fmt = (iso: string) => new Date(iso).toLocaleString()

export default function Overview() {
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      setData(await dashboardApi.summary(DAYS))
      setError(null)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not load the dashboard.')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    if (DEMO_MODE) return
    load()
    const t = setInterval(load, POLL_MS)
    return () => clearInterval(t)
  }, [load])

  if (DEMO_MODE) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-10">
        <DripHeading>Overview</DripHeading>
        <HauntedCard className="mt-6">
          <p className="font-semibold text-[#FF9A4D]">Demo Mode</p>
          <p className="mt-1 text-sm text-fog">The Overview shows real data from your backend. Set <code>VITE_DEMO_MODE=false</code> in <code>web/.env</code> and restart <code>npm run dev</code>.</p>
        </HauntedCard>
      </main>
    )
  }

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
      <div className="flex items-center justify-between gap-3">
        <DripHeading>Overview</DripHeading>
        <GlowButton variant="outline" onClick={() => { setLoading(true); load() }} disabled={loading}>
          <RefreshCw size={16} aria-hidden /> Refresh
        </GlowButton>
      </div>

      {error && <p role="alert" className="rounded-lg border border-blood p-3 text-sm text-[#FF6B86]">{error}</p>}
      {loading && !data && <p className="text-fog">Loading…</p>}

      {data && (
        <>
          {data.installations_linked === 0 && <LinkExtension onLinked={load} />}
          {data.installations_linked > 0 && data.total_events === 0 && (
            <HauntedCard><p className="text-sm text-fog">Extension linked. Waiting for the first browsing event. Nothing has been reported yet, which is not a safe verdict.</p></HauntedCard>
          )}

          <section aria-label={`Findings by status, last ${DAYS} days`}>
            <p className="mb-2 text-sm text-fog">Findings in the last {DAYS} days · {data.open_findings} open · {data.total_events} events recorded{data.last_event_at ? ` · last event ${fmt(data.last_event_at)}` : ''}</p>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
              {SEVERITIES.map((s: Severity) => (
                <HauntedCard key={s} className="p-4">
                  <SeverityBadge severity={s} />
                  <p className="mt-3 font-tech text-3xl text-moon">{data.status_counts[s] ?? 0}</p>
                </HauntedCard>
              ))}
            </div>
          </section>

          <div className="grid gap-6 lg:grid-cols-3">
            <HauntedCard className="lg:col-span-2" aria-labelledby="trend-h">
              <h2 id="trend-h" className="mb-3 font-tech text-lg text-moon">Flagged findings per day (HIGH RISK + SUSPICIOUS)</h2>
              <TrendChart days={data.trend} />
            </HauntedCard>
            <HealthPanel health={data.health} />
          </div>

          <HauntedCard aria-labelledby="rf-h">
            <h2 id="rf-h" className="mb-3 font-tech text-lg text-moon">Recent findings</h2>
            {data.recent_findings.length === 0 ? (
              <p className="text-sm text-fog">No findings yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-fog"><tr><th className="py-2 pr-4">Domain</th><th className="pr-4">Status</th><th className="pr-4">Score</th><th className="pr-4">Workflow</th><th className="pr-4">When</th><th>Why</th></tr></thead>
                  <tbody>
                    {data.recent_findings.map((f) => (
                      <tr key={f.id} className="border-t border-ghost align-top">
                        <td className="py-2 pr-4 font-mono text-moon">{f.domain}</td>
                        <td className="pr-4"><SeverityBadge severity={f.status_label} /></td>
                        <td className="pr-4 text-moon">{f.risk_score}</td>
                        <td className="pr-4 text-fog">{f.status}</td>
                        <td className="pr-4 whitespace-nowrap text-fog">{fmt(f.created_at)}</td>
                        <td className="text-fog">{f.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </HauntedCard>

          <HauntedCard aria-labelledby="re-h">
            <h2 id="re-h" className="mb-3 font-tech text-lg text-moon">Recent visits</h2>
            {data.recent_events.length === 0 ? (
              <p className="text-sm text-fog">No visits recorded yet.</p>
            ) : (
              <ul className="flex flex-col gap-2 text-sm">
                {data.recent_events.map((e) => (
                  <li key={e.id} className="flex flex-wrap items-center gap-3">
                    <span className="font-mono text-moon">{e.domain}</span>
                    <SeverityBadge severity={e.status_label} />
                    <span className="text-fog">{e.event_type} · {fmt(e.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </HauntedCard>

          <p className="text-xs text-fog"><strong className="text-moon">Data limitations:</strong> {data.limitations}</p>
        </>
      )}
    </main>
  )
}
