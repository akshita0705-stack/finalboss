import type { ElementType } from 'react'
import clsx from 'clsx'

const DRIPS = [
  { left: '8%', h: 18, d: 0 }, { left: '27%', h: 28, d: 1.2 }, { left: '46%', h: 14, d: 2.1 },
  { left: '63%', h: 24, d: 0.6 }, { left: '84%', h: 16, d: 1.7 },
]

/** Short (<= ~4 words) dripping headline. Drips are decorative and stop when effects are reduced. */
export function DripHeading({ children, as: Tag = 'h1', tone = 'pumpkin', className }: {
  children: string; as?: ElementType; tone?: 'pumpkin' | 'blood'; className?: string
}) {
  return (
    <Tag className={clsx('drip-text relative inline-block pb-6', tone === 'blood' && 'blood', className)}>
      {children}
      <span className="atmos" aria-hidden>
        {DRIPS.map((d, i) => (
          <span key={i} className="drip" style={{ left: d.left, ['--h' as string]: `${d.h}px`, animationDelay: `${d.d}s`, background: tone === 'blood' ? '#E5133A' : '#FF7A1A' }} />
        ))}
      </span>
    </Tag>
  )
}
