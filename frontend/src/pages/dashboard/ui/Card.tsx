import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { rise } from '../config/motion'

interface CardProps {
  title: string
  icon: LucideIcon
  // Right side of the title bar: a hint or a control.
  aside?: ReactNode
  className?: string
  bodyClassName?: string
  children: ReactNode
}

// A title bar on a tinted frame, the content on a surface inside it.
export function Card({
  title,
  icon: Icon,
  aside,
  className = '',
  bodyClassName = '',
  children,
}: CardProps) {
  return (
    <motion.section
      variants={rise}
      className={`flex min-w-0 flex-col rounded-2xl bg-fill/60 p-1 ring-1 ring-line ${className}`}
    >
      <header className="flex min-h-9 items-center gap-2 px-3 py-1.5">
        <Icon size={16} strokeWidth={2} className="shrink-0 text-fg-3" aria-hidden="true" />
        <h2 className="truncate text-sm font-medium">{title}</h2>
        {aside && (
          <div className="ml-auto flex shrink-0 items-center text-xs text-fg-3">{aside}</div>
        )}
      </header>
      <div
        className={`flex flex-1 flex-col rounded-xl bg-layer p-4 ring-1 ring-line ${bodyClassName}`}
      >
        {children}
      </div>
    </motion.section>
  )
}
