import type { ReactNode } from 'react'
import type { Comparison } from '../lib/metrics'

const toneClass: Record<Comparison['tone'], string> = {
  good: 'text-positive',
  bad: 'text-negative',
  neutral: 'text-fg-3',
}

interface FigureProps {
  label: string
  value: string
  // A line under the value: the norm, the number of ratings.
  note?: ReactNode
  comparison?: Comparison | null
  emphasis?: 'negative'
}

export function Figure({ label, value, note, comparison, emphasis }: FigureProps) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <span className="text-sm text-fg-2">{label}</span>
      <span className="flex flex-wrap items-baseline gap-x-2">
        <span
          className={`text-[28px] leading-9 font-semibold ${emphasis === 'negative' ? 'text-negative' : ''}`}
        >
          {value}
        </span>
        {comparison && (
          <span className={`text-sm font-medium ${toneClass[comparison.tone]}`}>
            {comparison.text}
          </span>
        )}
      </span>
      {note && <span className="text-xs text-fg-3">{note}</span>}
    </div>
  )
}
