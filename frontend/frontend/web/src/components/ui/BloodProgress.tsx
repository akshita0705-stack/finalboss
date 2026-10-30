/** Blood-drip progress bar for long operations. */
export function BloodProgress({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div role="progressbar" aria-label={label} aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} className="w-full">
      <div className="relative h-3 rounded-full bg-surface-2">
        <div className="h-3 rounded-full bg-blood transition-[width] duration-200" style={{ width: `${pct}%` }} />
        <span className="atmos absolute -bottom-2 h-3 w-2 rounded-b-full bg-blood" style={{ left: `calc(${pct}% - 8px)` }} aria-hidden />
      </div>
      <p className="mt-2 text-xs text-fog">{label} {Math.round(pct)}%</p>
    </div>
  )
}
