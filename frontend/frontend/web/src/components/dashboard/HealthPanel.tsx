import { CheckCircle2, TriangleAlert } from 'lucide-react'
import { HauntedCard } from '@/components/ui/HauntedCard'
import type { DashboardSummary } from '@/types/dashboard'

export function HealthPanel({ health }: { health: DashboardSummary['health'] }) {
  const items = [health.backend, health.graph, health.threat_provider]
  return (
    <HauntedCard aria-labelledby="health-h">
      <h2 id="health-h" className="mb-3 font-tech text-lg text-moon">System health</h2>
      <ul className="flex flex-col gap-3">
        {items.map((h) => (
          <li key={h.label} className="flex items-start gap-3">
            {h.ok
              ? <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-[#39FF88]" aria-hidden />
              : <TriangleAlert size={18} className="mt-0.5 shrink-0 text-[#FF9A4D]" aria-hidden />}
            <div>
              <p className="text-sm font-semibold text-moon">{h.label}: {h.ok ? 'OK' : 'Needs attention'}</p>
              <p className="text-xs text-fog">{h.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </HauntedCard>
  )
}
