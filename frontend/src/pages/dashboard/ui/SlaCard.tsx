import { motion, useReducedMotion } from 'framer-motion'
import { Timer } from 'lucide-react'
import type { Dashboard } from '../api/dashboard'
import { bullet } from '../lib/bullet'
import { compare, formatDuration, formatShare, previousNote } from '../lib/metrics'
import { AnimatedNumber } from './AnimatedNumber'
import { Card } from './Card'
import { Delta } from './Delta'

interface SlaRowProps {
  label: string
  hours: number | null
  previousHours: number | null
  normHours: number
  onTime: { value: number | null; previous: number | null }
}

function SlaRow({ label, hours, previousHours, normHours, onTime }: SlaRowProps) {
  const reduceMotion = useReducedMotion()
  const scale = hours === null ? null : bullet(hours, normHours)
  const comparison = compare({ value: hours, previous: previousHours }, 'percent', 'down')
  const onTimeChange = compare(onTime, 'points', 'up')

  return (
    <div className="flex min-w-0 flex-col gap-3">
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="text-fg-2">{label}</span>
        <span className="text-xs text-fg-3">норма {normHours} ч</span>
      </div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="text-[28px] leading-8 font-semibold">
          {hours === null ? '—' : <AnimatedNumber value={hours} format={formatDuration} />}
        </span>
        {comparison && <Delta comparison={comparison} />}
      </div>
      <div className="relative h-2 rounded-full bg-fill">
        {scale && (
          <>
            <motion.span
              className={`absolute inset-y-0 left-0 w-full origin-left rounded-full ${
                scale.over ? 'bg-negative' : 'bg-positive'
              }`}
              initial={reduceMotion ? false : { scaleX: 0 }}
              animate={{ scaleX: scale.fill }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            />
            <span
              className="absolute -top-1 h-4 w-0.5 -translate-x-1/2 rounded-full bg-fg"
              style={{ left: `${scale.mark * 100}%` }}
              title={`Норма: ${normHours} ч`}
            />
          </>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
        <span className="text-fg-2">В срок</span>
        <span className="font-semibold">{formatShare(onTime.value)}</span>
        {onTimeChange && <Delta comparison={onTimeChange} />}
        <span className="text-xs text-fg-3">{previousNote(onTime.previous, formatShare)}</span>
      </div>
    </div>
  )
}

export function SlaCard({ data }: { data: Dashboard }) {
  const { summary, sla } = data
  const minutesToHours = (minutes: number | null) => (minutes === null ? null : minutes / 60)
  return (
    <Card title="Сроки" icon={Timer}>
      <div className="grid gap-x-8 gap-y-6 md:grid-cols-2">
        <SlaRow
          label="Реакция"
          hours={minutesToHours(summary.reaction_minutes.value)}
          previousHours={minutesToHours(summary.reaction_minutes.previous)}
          normHours={sla.reaction_hours}
          onTime={summary.reaction_on_time}
        />
        <SlaRow
          label="Решение"
          hours={summary.resolution_hours.value}
          previousHours={summary.resolution_hours.previous}
          normHours={sla.resolution_hours}
          onTime={summary.resolution_on_time}
        />
      </div>
      <p className="mt-4 text-xs text-fg-3">Столбик — среднее время, черта — норма.</p>
    </Card>
  )
}
