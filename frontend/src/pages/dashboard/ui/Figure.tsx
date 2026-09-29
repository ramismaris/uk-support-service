import { motion, useReducedMotion } from 'framer-motion'
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Comparison } from '../lib/metrics'
import { AnimatedNumber } from './AnimatedNumber'

const EMPTY = '—'

const deltaStyle: Record<Comparison['tone'], string> = {
  good: 'bg-positive/12 text-positive',
  bad: 'bg-negative/12 text-negative',
  neutral: 'bg-fill text-fg-3',
}

export function Delta({ comparison }: { comparison: Comparison }) {
  const Icon = comparison.text.startsWith('+')
    ? ArrowUpRight
    : comparison.text.startsWith('−')
      ? ArrowDownRight
      : Minus
  return (
    <span
      className={`inline-flex items-center gap-0.5 rounded-full py-0.5 pr-2 pl-1 text-xs font-medium ${deltaStyle[comparison.tone]}`}
    >
      <Icon size={14} strokeWidth={2.25} aria-hidden="true" />
      {comparison.text}
    </span>
  )
}

// A share of 0..1 as a filled track: how close to "everything on time".
export function Meter({ share }: { share: number }) {
  const reduceMotion = useReducedMotion()
  return (
    <span className="block h-1.5 overflow-hidden rounded-full bg-brand/15">
      <motion.span
        className="block h-full origin-left rounded-full bg-brand"
        initial={reduceMotion ? false : { scaleX: 0 }}
        animate={{ scaleX: share }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      />
    </span>
  )
}

interface FigureProps {
  label: string
  value: number | null
  format: (value: number) => string
  // A line under the value: the previous period, the number of ratings.
  note?: ReactNode
  comparison?: Comparison | null
  // Under the value: a meter, stars.
  children?: ReactNode
}

export function Figure({ label, value, format, note, comparison, children }: FigureProps) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="text-sm text-fg-2">{label}</span>
      <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[28px] leading-9 font-semibold">
          {value === null ? EMPTY : <AnimatedNumber value={value} format={format} />}
        </span>
        {comparison && <Delta comparison={comparison} />}
      </span>
      {children}
      {note && <span className="text-xs text-fg-3">{note}</span>}
    </div>
  )
}
