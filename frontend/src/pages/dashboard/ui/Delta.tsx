import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import type { Comparison } from '../lib/metrics'

const deltaStyle: Record<Comparison['tone'], string> = {
  good: 'bg-positive/12 text-positive',
  bad: 'bg-negative/12 text-negative',
  neutral: 'bg-fill text-fg-3',
}

// The change against the previous period; the colour says whether it is good.
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
