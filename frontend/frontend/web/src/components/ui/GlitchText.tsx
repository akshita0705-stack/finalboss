import type { ElementType, ReactNode } from 'react'

/** RGB-split glitch on hover/focus (300ms). Decorative headings only. */
export function GlitchText({ children, as: Tag = 'span', className = '' }: { children: string; as?: ElementType; className?: string; }) {
  return <Tag className={`glitch ${className}`} data-text={children} tabIndex={0}>{children as ReactNode}</Tag>
}
