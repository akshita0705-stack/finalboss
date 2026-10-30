import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Download, Printer, Skull, Table2, BarChart3 } from 'lucide-react'
import { DripHeading } from '@/components/ui/DripHeading'
import { HauntedCard } from '@/components/ui/HauntedCard'
import { GlowButton } from '@/components/ui/GlowButton'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { BloodProgress } from '@/components/ui/BloodProgress'
import { TrendChart } from '@/components/reports/TrendChart'
import { Breakdown } from '@/components/reports/Breakdown'
import { downloadCsv } from '@/components/reports/exportCsv'
import { loadReport } from '@/services/demo/reports'
import { SEVERITIES, type ReportData, type Severity } from '@/types'

const RANGES = [7, 14, 30] as const

function Skeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-live="polite">
      <p className="text-fog">The spirits are gathering the report…</p>
      {[0, 1, 2].map((i) => <div key={i} className="shimmer h-40 rounded-xl border border-ghost" />)}
    </div>
  )
}

export default function Reports() {
  const [range, setRange] = useState<(typeof RANGES)[number]>(7)
  const [data, setData] = useState<ReportData | null>(null)
  const [error, setError] = useState(false)
  const [tableView, setTableView] = useState(false)
  const [exporting, setExporting] = useState(0)

  useEffect(() => {
    let live = true
    setData(null); setError(false)
    loadReport(range).then((r) => live && setData(r)).catch(() => live && setError(true))
    return () => { live = false }
  }, [range])

  const totals = useMemo(() => {
    const t = Object.fromEntries(SEVERITIES.map((s) => [s, 0])) as Record<Severity, number>
    data?.days.forEach((d) => SEVERITIES.forEach((s) => { t[s] += d.counts[s] }))
    return t
  }, [data])

  const exportCsv = () => {
    if (!data || exporting) return
    setExporting(1)
    const id = setInterval(() => setExporting((p) => {
      if (p >= 100) { clearInterval(id); downloadCsv(data); setTimeout(() => setExporting(0), 300); return 100 }
      return Math.min(100, p + 20)
    }), 120)
  }

  return (
    <motion.main initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-5xl px-4 pb-24 pt-6 sm:px-6">
      <p className="print-hide mb-4 inline-block rounded border border-witch/60 bg-witch/10 px-2 py-1 font-tech text-xs tracking-widest text-[#B79BFF]">
        DEMO MODE – SYNTHETIC DATA
      </p>
      <div>
        <DripHeading tone="pumpkin" className="text-5xl sm:text-6xl">Reports</DripHeading>
        <p className="font-tech text-lg text-moon">Every ghost we caught, on the record.</p>
      </div>

      <div className="print-hide mt-6 flex flex-wrap items-center gap-3">
        <div role="group" aria-label="Date range" className="flex overflow-hidden rounded-lg border border-ghost">
          {RANGES.map((r) => (
            <button key={r} onClick={() => setRange(r)} aria-pressed={range === r}
              className={`px-4 py-2 font-tech text-sm transition ${range === r ? 'bg-pumpkin text-void' : 'bg-surface text-moon hover:bg-surface-2'}`}>
              Last {r} days
            </button>
          ))}
        </div>
        <GlowButton variant="outline" onClick={exportCsv} disabled={!data || exporting > 0}><Download size={16} aria-hidden />Export CSV</GlowButton>
        <GlowButton variant="outline" onClick={() => window.print()} disabled={!data}><Printer size={16} aria-hidden />Save as PDF</GlowButton>
      </div>
      {exporting > 0 && <div className="print-hide mt-4 max-w-md"><BloodProgress value={exporting} label="Summoning your CSV…" /></div>}

      <div className="mt-6 space-y-6">
        {error && (
          <HauntedCard role="alert" className="border-blood">
            <h2 className="font-tech text-lg text-[#FF6B86]">The report failed to rise from the grave</h2>
            <p className="mt-1 text-sm text-fog">We couldn’t load this period. This is not a safe verdict. Try again.</p>
            <GlowButton className="mt-3" variant="danger" onClick={() => setRange(range)}>Retry</GlowButton>
          </HauntedCard>
        )}
        {!data && !error && <Skeleton />}

        {data && (
          <>
            {totals.HIGH_RISK > 0 ? (
              <div role="alert" className="alert-pulse flex items-center gap-4 rounded-xl border border-blood bg-blood/10 p-4">
                <Skull size={36} className="shrink-0 text-[#FF6B86]" aria-hidden />
                <div>
                  <p className="drip-text blood text-3xl">HIGH RISK</p>
                  <p className="text-sm text-moon"><strong>{totals.HIGH_RISK}</strong> high-risk findings in this period. Review the domains below.</p>
                </div>
              </div>
            ) : (
              <HauntedCard><p className="text-moon">No HIGH RISK findings in the signals checked for this period.</p></HauntedCard>
            )}

            <HauntedCard aria-labelledby="sum-h">
              <h2 id="sum-h" className="font-tech text-xl">Daily summary</h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                {SEVERITIES.map((s) => (
                  <div key={s} className="rounded-lg border border-ghost bg-surface-2 p-3">
                    <dt><SeverityBadge severity={s} /></dt>
                    <dd className="mt-2 font-mono text-2xl text-moon">{totals[s]}</dd>
                  </div>
                ))}
              </dl>
            </HauntedCard>

            <HauntedCard aria-labelledby="trend-h">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 id="trend-h" className="font-tech text-xl">Flagged findings per day (HIGH RISK + SUSPICIOUS)</h2>
                <button onClick={() => setTableView((v) => !v)} aria-pressed={tableView}
                  className="print-hide inline-flex items-center gap-1.5 rounded-lg border border-ghost px-3 py-1.5 text-sm text-moon hover:border-pumpkin">
                  {tableView ? <BarChart3 size={14} aria-hidden /> : <Table2 size={14} aria-hidden />}{tableView ? 'Chart view' : 'Table view'}
                </button>
              </div>
              {tableView ? (
                <div className="max-h-72 overflow-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-surface text-fog"><tr><th className="py-1 pr-4">Date</th><th className="pr-4">HIGH RISK</th><th className="pr-4">SUSPICIOUS</th><th>Total</th></tr></thead>
                    <tbody>{data.days.map((d) => (
                      <tr key={d.date} className="border-t border-ghost"><td className="py-1 pr-4 font-mono">{d.date}</td><td>{d.counts.HIGH_RISK}</td><td>{d.counts.SUSPICIOUS}</td><td>{d.counts.HIGH_RISK + d.counts.SUSPICIOUS}</td></tr>
                    ))}</tbody>
                  </table>
                </div>
              ) : <TrendChart days={data.days} />}
            </HauntedCard>

            <HauntedCard aria-labelledby="br-h">
              <h2 id="br-h" className="mb-4 font-tech text-xl">Severity breakdown</h2>
              <Breakdown totals={totals} />
            </HauntedCard>

            <HauntedCard aria-labelledby="top-h">
              <h2 id="top-h" className="mb-3 font-tech text-xl">Top concerning domains</h2>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[40rem] text-left text-sm">
                  <thead className="text-fog"><tr><th className="py-2 pr-4">Domain</th><th className="pr-4">Status</th><th className="pr-4">Visits</th><th>Why</th></tr></thead>
                  <tbody>{data.topDomains.map((d) => (
                    <tr key={d.hostname} className="border-t border-ghost align-top">
                      <td className="py-2 pr-4 font-mono text-moon">{d.hostname}</td>
                      <td className="pr-4"><SeverityBadge severity={d.severity} /></td>
                      <td className="pr-4 font-mono">{d.visits}</td>
                      <td className="text-fog">{d.reason}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            </HauntedCard>

            <footer className="rounded-xl border border-dashed border-ghost p-4 text-xs text-fog">
              <p><strong className="text-moon">Period:</strong> <span className="font-mono">{data.from}</span> to <span className="font-mono">{data.to}</span> ({range} days).</p>
              <p className="mt-1"><strong className="text-moon">Data limitations:</strong> Only normalised domains are reported, never full URLs or page content. Encrypted traffic is not inspected, and external domains appear only where reliably observable. A missing result is not a safe verdict, and LOW OBSERVED RISK means no significant issue was found in the signals checked. {data.synthetic && 'All figures here are synthetic demo data.'}</p>
            </footer>
          </>
        )}
      </div>
    </motion.main>
  )
}
