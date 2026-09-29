import { motion, useReducedMotion } from 'framer-motion'
import { List, Radar, Tags } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import type { Dashboard } from '../api/dashboard'
import { categoryRows, type CategoryRow } from '../lib/categories'
import { formatDuration } from '../lib/metrics'
import { Card } from './Card'

function Row({ row }: { row: CategoryRow }) {
  const reduceMotion = useReducedMotion()
  return (
    <li className="flex flex-col gap-1.5">
      <div className="flex items-baseline gap-2 text-sm">
        <span className="truncate" title={row.title}>
          {row.title}
        </span>
        <span className="ml-auto font-medium tabular-nums">{row.created}</span>
        <span className="w-9 text-right text-xs text-fg-3 tabular-nums">
          {Math.round(row.share * 100)}%
        </span>
      </div>
      {/* The bar is the category's share of all requests: it is only full when it is the only one. */}
      <div className="h-1.5 rounded-full bg-fill">
        <motion.div
          className="h-full origin-left rounded-full bg-brand"
          initial={reduceMotion ? false : { scaleX: 0 }}
          animate={{ scaleX: row.share }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
      {row.hours !== null && (
        <span className={`text-xs ${row.slow ? 'text-negative' : 'text-fg-3'}`}>
          Решают {formatDuration(row.hours)}
          {row.slow && ' — дольше нормы'}
        </span>
      )}
    </li>
  )
}

type View = 'list' | 'radar'

const VIEWS = [
  { key: 'list', label: 'Список', icon: List },
  { key: 'radar', label: 'Радар', icon: Radar },
] as const

function ViewSwitch({ value, onChange }: { value: View; onChange: (view: View) => void }) {
  return (
    <div role="radiogroup" aria-label="Вид" className="flex rounded-lg bg-fill p-0.5">
      {VIEWS.map(({ key, label, icon: Icon }) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={key === value}
          onClick={() => onChange(key)}
          className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium transition-colors ${
            key === value ? 'bg-layer text-fg shadow-sm' : 'text-fg-2 hover:text-fg'
          }`}
        >
          <Icon size={14} aria-hidden="true" />
          {label}
        </button>
      ))}
    </div>
  )
}

// Recharts is heavy and the dashboard already pulls it for the daily chart: one more small chunk.
const CategoryRadar = lazy(() => import('./CategoryRadar'))

// A radar needs at least three corners to be a shape.
const MIN_RADAR_CATEGORIES = 3

export function Categories({ data }: { data: Dashboard }) {
  const [view, setView] = useState<View>('list')
  const rows = categoryRows(data.categories, data.sla.resolution_hours)
  const { questions } = data
  const radar = view === 'radar' && rows.length >= MIN_RADAR_CATEGORIES

  return (
    <Card
      title="Заявки по категориям"
      icon={Tags}
      aside={
        rows.length >= MIN_RADAR_CATEGORIES ? <ViewSwitch value={view} onChange={setView} /> : null
      }
      bodyClassName="gap-4"
    >
      {rows.length === 0 ? (
        <p className="text-sm text-fg-3">За период заявок не было</p>
      ) : radar ? (
        <div className="min-h-[300px]">
          <Suspense fallback={null}>
            <CategoryRadar rows={rows} />
          </Suspense>
        </div>
      ) : (
        <ul className="flex flex-col gap-4">
          {rows.map((row) => (
            <Row key={row.id} row={row} />
          ))}
        </ul>
      )}
      <p className="flex items-baseline gap-2 border-t border-line pt-3 text-sm">
        <span className="text-fg-2">Вопросы отдельно</span>
        <span className="ml-auto font-medium tabular-nums">{questions.created}</span>
        {questions.resolution_hours !== null && (
          <span className="text-xs text-fg-3">
            решают {formatDuration(questions.resolution_hours)}
          </span>
        )}
      </p>
    </Card>
  )
}
