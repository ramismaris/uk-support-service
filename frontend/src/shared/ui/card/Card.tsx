import { motion, type Variants } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

const rise: Variants = {
  hidden: { opacity: 0, y: 12 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] } },
}

interface CardProps {
  title: string
  icon: LucideIcon
  aside?: ReactNode
  className?: string
  bodyClassName?: string
  children: ReactNode
}

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
      <header className="flex min-h-9 flex-wrap items-center gap-x-2 gap-y-1 px-3 py-1.5">
        <Icon size={16} strokeWidth={2} className="shrink-0 text-fg-3" aria-hidden="true" />
        <h2 className="text-sm font-medium">{title}</h2>
        {aside && <div className="ml-auto flex items-center text-xs text-fg-3">{aside}</div>}
      </header>
      <div
        className={`@container flex flex-1 flex-col rounded-xl bg-layer p-4 ring-1 ring-line ${bodyClassName}`}
      >
        {children}
      </div>
    </motion.section>
  )
}
