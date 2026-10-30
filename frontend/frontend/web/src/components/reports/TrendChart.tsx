import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipProps } from 'recharts'
import type { DailySummary } from '@/types'

interface Point { date: string; high: number; suspicious: number; flagged: number }

function ChartTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload as Point
  return (
    <div className="rounded-lg border border-ghost bg-surface-2 px-3 py-2 text-xs text-moon shadow-lg">
      <p className="mb-1 font-mono">{p.date}</p>
      <p>Flagged total: <strong>{p.flagged}</strong></p>
      <p className="text-fog">HIGH RISK {p.high} · SUSPICIOUS {p.suspicious}</p>
    </div>
  )
}

/** Single series (HIGH RISK + SUSPICIOUS per day); the card title names it, so no legend box. */
export function TrendChart({ days }: { days: DailySummary[] }) {
  const data: Point[] = days.map((d) => ({
    date: d.date, high: d.counts.HIGH_RISK, suspicious: d.counts.SUSPICIOUS, flagged: d.counts.HIGH_RISK + d.counts.SUSPICIOUS,
  }))
  const tick = { fill: '#9AA3B2', fontSize: 12 }
  return (
    <div className="h-72 w-full" role="img" aria-label="Area chart of HIGH RISK plus SUSPICIOUS findings per day. A table view is available below.">
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 24, left: 4 }}>
          <defs>
            <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#E5133A" stopOpacity={0.55} />
              <stop offset="100%" stopColor="#FF7A1A" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="trendStroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#FF7A1A" /><stop offset="100%" stopColor="#E5133A" />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#2A2538" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="date" tick={tick} tickFormatter={(v: string) => v.slice(5)} minTickGap={24} stroke="#2A2538"
            label={{ value: 'Date (MM-DD)', position: 'insideBottom', offset: -14, fill: '#9AA3B2', fontSize: 12 }} />
          <YAxis allowDecimals={false} tick={tick} stroke="#2A2538" width={44}
            label={{ value: 'Flagged findings', angle: -90, position: 'insideLeft', fill: '#9AA3B2', fontSize: 12 }} />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#F3E9C6', strokeOpacity: 0.4 }} />
          <Area type="monotone" dataKey="flagged" stroke="url(#trendStroke)" strokeWidth={2} fill="url(#trendFill)"
            dot={false} activeDot={{ r: 5, stroke: '#14121C', strokeWidth: 2, fill: '#FF7A1A' }} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
