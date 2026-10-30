import type { ButtonHTMLAttributes } from 'react'
import clsx from 'clsx'

type Variant = 'primary' | 'outline' | 'danger'

const styles: Record<Variant, string> = {
  primary: 'bg-pumpkin text-void hover:bg-pumpkin-glow hover:shadow-pumpkin',
  outline: 'border border-pumpkin text-pumpkin hover:bg-pumpkin/10 hover:shadow-pumpkin',
  danger: 'border border-blood text-[#FF6B86] hover:bg-blood/10 hover:shadow-blood',
}

export function GlowButton({ variant = 'primary', className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button {...rest}
      className={clsx('inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 font-tech text-sm font-semibold transition',
        'disabled:cursor-not-allowed disabled:opacity-50', styles[variant], className)} />
  )
}
