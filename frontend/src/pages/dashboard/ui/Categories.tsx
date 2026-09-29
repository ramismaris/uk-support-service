import { motion, useReducedMotion } from 'framer-motion'
import type { components } from '@/shared/api'
import type { DashboardCategory } from '../api/dashboard'
import { formatDuration } from '../lib/metrics'

type Questions = components['schemas']['DashboardQuestions']

function Row({
  title,
  created,
  resolutionHours,
  max,
}: {
  title: string
  created: number
  resolutionHours: number | null
  max: number
}) {
  const reduceMotion = useReducedMotion()
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_3rem_4.5rem] items-center gap-x-3 gap-y-1.5 py-2 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_3rem_4.5rem]">
      <span className="truncate text-sm" title={title}>
        {title}
      </span>
      {/* One colour for every bar: the length already tells the amount. */}
      <span className="col-span-3 row-start-2 h-1.5 rounded-full bg-fill sm:col-span-1 sm:row-start-auto">
        <motion.span
          className="block h-full origin-left rounded-full bg-brand"
          initial={reduceMotion ? false : { scaleX: 0 }}
          animate={{ scaleX: max > 0 ? created / max : 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      </span>
      <span className="text-right text-sm font-medium tabular-nums">{created}</span>
      <span className="text-right text-sm text-fg-2 tabular-nums">
        {formatDuration(resolutionHours)}
      </span>
    </li>
  )
}

export function Categories({
  categories,
  questions,
}: {
  categories: DashboardCategory[]
  questions: Questions
}) {
  const max = Math.max(questions.created, ...categories.map((category) => category.created))

  if (categories.length === 0 && questions.created === 0) {
    return <p className="text-sm text-fg-3">За период обращений не было</p>
  }

  return (
    <div className="flex flex-col">
      <div className="grid grid-cols-[minmax(0,1fr)_3rem_4.5rem] gap-x-3 text-xs text-fg-3 sm:grid-cols-[minmax(0,14rem)_minmax(0,1fr)_3rem_4.5rem]">
        <span>Заявки</span>
        <span className="hidden sm:block" />
        <span className="text-right">Шт.</span>
        <span className="text-right">Решение</span>
      </div>
      <ul className="divide-y divide-line">
        {categories.map((category) => (
          <Row
            key={category.category_id}
            title={category.title}
            created={category.created}
            resolutionHours={category.resolution_hours}
            max={max}
          />
        ))}
      </ul>
      <ul className="mt-2 border-t border-line pt-2">
        <Row
          title="Вопросы"
          created={questions.created}
          resolutionHours={questions.resolution_hours}
          max={max}
        />
      </ul>
    </div>
  )
}
