import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Comparison } from '../lib/metrics'
import { AnimatedNumber } from './AnimatedNumber'
import { Card } from './Card'
import { Delta } from './Delta'

interface StatCardProps {
  title: string
  icon: LucideIcon
  value: number | null
  format: (value: number) => string
  comparison?: Comparison | null
  note?: string
  chart?: ReactNode
  children?: ReactNode
}

export function StatCard({
  title,
  icon,
  value,
  format,
  comparison,
  note,
  chart,
  children,
}: StatCardProps) {
  return (
    <Card title={title} icon={icon} bodyClassName="gap-3">
      <div className="flex flex-wrap items-end justify-between gap-x-3 gap-y-2">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-[32px] leading-9 font-semibold">
              {value === null ? '—' : <AnimatedNumber value={value} format={format} />}
            </span>
            {comparison && <Delta comparison={comparison} />}
          </span>
          {note && <span className="text-xs text-fg-3">{note}</span>}
        </div>
        {chart}
      </div>
      {children}
    </Card>
  )
}
