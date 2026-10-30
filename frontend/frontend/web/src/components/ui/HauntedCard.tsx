import type { HTMLAttributes } from 'react'
import clsx from 'clsx'

/** Card with pumpkin hover glow, slight lift and a faint cobweb in the corner. */
export function HauntedCard({ className, children, ...rest }: HTMLAttributes<HTMLElement>) {
  return (
    <section {...rest}
      className={clsx('cobweb relative rounded-xl border border-ghost bg-surface p-5 transition duration-200',
        'hover:-translate-y-0.5 hover:border-pumpkin hover:shadow-pumpkin print:break-inside-avoid', className)}>
      {children}
    </section>
  )
}
