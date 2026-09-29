import { Button } from '@maxhub/max-ui'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { ChartColumn } from 'lucide-react'
import { lazy, Suspense, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import { EmptyState } from '@/shared/ui/empty-state'
import { NavMenuButton } from '@/widgets/app-shell'
import { PERIODS, type Dashboard, type Period } from '../api/dashboard'
import { SERIES } from '../config/series'
import { compare, formatDuration, formatRating, formatShare, previousNote } from '../lib/metrics'
import { formatDay, formatRange, parsePeriod } from '../lib/period'
import { useDashboard } from '../model/use-dashboard'
import { Categories } from './Categories'
import { Figure, Meter } from './Figure'
import { NowStrip } from './NowStrip'
import { Stars } from './Stars'

// Recharts is heavy: only the admin opening the dashboard downloads it.
const DailyChart = lazy(() => import('./DailyChart'))

const CHART_HEIGHT = 'h-60'

const count = (value: number) => String(Math.round(value))
const minutesAsDuration = (minutes: number) => formatDuration(minutes / 60)

// The panels come in one after another when the dashboard opens.
const stagger: Variants = { shown: { transition: { staggerChildren: 0.06 } } }
const rise: Variants = {
  hidden: { opacity: 0, y: 12 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] } },
}

function Panel({
  title,
  hint,
  className = '',
  children,
}: {
  title: string
  hint?: string
  className?: string
  children: ReactNode
}) {
  return (
    <motion.section
      variants={rise}
      className={`flex min-w-0 flex-col gap-4 rounded-2xl bg-layer p-4 ring-1 ring-line lg:p-5 ${className}`}
    >
      <header className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
        <h2 className="font-semibold">{title}</h2>
        {hint && <span className="text-xs text-fg-3">{hint}</span>}
      </header>
      {children}
    </motion.section>
  )
}

function PeriodSwitch({ value, onChange }: { value: Period; onChange: (period: Period) => void }) {
  return (
    <div role="radiogroup" aria-label="Период" className="flex rounded-xl bg-fill p-0.5">
      {PERIODS.map((period) => (
        <button
          key={period}
          type="button"
          role="radio"
          aria-checked={period === value}
          onClick={() => onChange(period)}
          className="relative rounded-[10px] px-3 py-1.5 text-sm font-medium"
        >
          {period === value && (
            <motion.span
              layoutId="period-pill"
              className="absolute inset-0 rounded-[10px] bg-layer shadow-sm"
              transition={{ type: 'spring', bounce: 0, duration: 0.3 }}
            />
          )}
          <span
            className={`relative transition-colors ${period === value ? 'text-fg' : 'text-fg-2 hover:text-fg'}`}
          >
            {period} дн
          </span>
        </button>
      ))}
    </div>
  )
}

function DailyTable({ days }: { days: Dashboard['daily'] }) {
  return (
    <details className="text-sm">
      <summary className="cursor-pointer text-fg-2 select-none hover:text-fg">Таблицей</summary>
      <div className="mt-2 max-h-72 overflow-y-auto">
        <table className="w-full tabular-nums">
          <thead className="sticky top-0 bg-layer text-left text-fg-3">
            <tr>
              <th className="py-1 font-normal">День</th>
              {SERIES.map((series) => (
                <th key={series.key} className="py-1 text-right font-normal">
                  {series.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {days.toReversed().map((day) => (
              <tr key={day.date} className="border-t border-line">
                <td className="py-1">{formatDay(day.date)}</td>
                <td className="py-1 text-right">{day.created}</td>
                <td className="py-1 text-right">{day.closed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

function DashboardBody({ data }: { data: Dashboard }) {
  const { now, summary, sla } = data
  const reduceMotion = useReducedMotion()
  const reaction = summary.reaction_minutes

  return (
    <motion.div
      className="grid gap-4 lg:grid-cols-4"
      variants={stagger}
      initial={reduceMotion ? false : 'hidden'}
      animate="shown"
    >
      <Panel title="Сейчас" hint="Открытые обращения" className="lg:col-span-4">
        <NowStrip now={now} />
      </Panel>

      <Panel title="Нагрузка" hint={`К прошлым ${data.period_days} дням`}>
        <div className="grid grid-cols-2 gap-4">
          <Figure
            label="Поступило"
            value={summary.created.value}
            format={count}
            comparison={compare(summary.created, 'percent', 'up')}
            note={previousNote(summary.created.previous, String)}
          />
          <Figure
            label="Закрыто"
            value={summary.closed.value}
            format={count}
            comparison={compare(summary.closed, 'percent', 'up')}
            note={previousNote(summary.closed.previous, String)}
          />
        </div>
      </Panel>

      <Panel
        title="Сроки"
        hint={`Норма: реакция ${sla.reaction_hours} ч, решение ${sla.resolution_hours} ч`}
        className="lg:col-span-2"
      >
        <div className="grid grid-cols-2 gap-x-4 gap-y-5">
          <Figure
            label="Реакция в среднем"
            value={reaction.value}
            format={minutesAsDuration}
            comparison={compare(reaction, 'percent', 'down')}
            note={previousNote(reaction.previous, minutesAsDuration)}
          />
          <Figure
            label="Реакция в срок"
            value={summary.reaction_on_time.value}
            format={formatShare}
            comparison={compare(summary.reaction_on_time, 'points', 'up')}
            note={previousNote(summary.reaction_on_time.previous, formatShare)}
          >
            {summary.reaction_on_time.value !== null && (
              <Meter share={summary.reaction_on_time.value} />
            )}
          </Figure>
          <Figure
            label="Решение в среднем"
            value={summary.resolution_hours.value}
            format={formatDuration}
            comparison={compare(summary.resolution_hours, 'percent', 'down')}
            note={previousNote(summary.resolution_hours.previous, formatDuration)}
          />
          <Figure
            label="Решено в срок"
            value={summary.resolution_on_time.value}
            format={formatShare}
            comparison={compare(summary.resolution_on_time, 'points', 'up')}
            note={previousNote(summary.resolution_on_time.previous, formatShare)}
          >
            {summary.resolution_on_time.value !== null && (
              <Meter share={summary.resolution_on_time.value} />
            )}
          </Figure>
        </div>
      </Panel>

      <Panel title="Оценки жильцов" hint="По закрытым за период">
        <Figure
          label="Средняя оценка из 5"
          value={summary.rating.value}
          format={formatRating}
          comparison={compare(summary.rating, 'difference', 'up')}
          note={
            summary.rating.count > 0
              ? [
                  `Оценок: ${summary.rating.count}`,
                  previousNote(summary.rating.previous, formatRating),
                ]
                  .filter(Boolean)
                  .join('. ')
              : 'Оценок пока нет'
          }
        >
          {summary.rating.value !== null && <Stars rating={summary.rating.value} />}
        </Figure>
      </Panel>

      <Panel title="По дням" className="lg:col-span-4">
        <ul className="-mt-2 flex flex-wrap gap-4 text-sm text-fg-2">
          {SERIES.map((series) => (
            <li key={series.key} className="flex items-center gap-2">
              <span className="h-0.5 w-4 rounded-full" style={{ backgroundColor: series.color }} />
              {series.label}
            </li>
          ))}
        </ul>
        <Suspense fallback={<div className={CHART_HEIGHT} />}>
          <DailyChart days={data.daily} />
        </Suspense>
        <DailyTable days={data.daily} />
      </Panel>

      <Panel
        title="По категориям"
        hint="Поступило за период и среднее время решения"
        className="lg:col-span-4"
      >
        <Categories categories={data.categories} questions={data.questions} />
      </Panel>
    </motion.div>
  )
}

export function DashboardPage() {
  const [search, setSearch] = useSearchParams()
  const period = parsePeriod(search.get('period'))
  const dashboard = useDashboard(period)

  const body = () => {
    if (dashboard.isPending) {
      return <div className="m-auto text-sm text-fg-3">Загрузка…</div>
    }
    if (dashboard.isError) {
      return (
        <EmptyState
          icon={<ChartColumn size={48} strokeWidth={1.5} />}
          title="Не удалось загрузить дашборд"
          text={dashboard.error.message}
          action={<Button onClick={() => void dashboard.refetch()}>Повторить</Button>}
        />
      )
    }
    return (
      // While another period loads, the previous one stays, dimmed, instead of a blank page.
      <div
        className={`mx-auto w-full max-w-6xl p-4 transition-opacity lg:p-6 ${
          dashboard.isPlaceholderData ? 'opacity-60' : ''
        }`}
      >
        <DashboardBody data={dashboard.data} />
      </div>
    )
  }

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-y-auto">
      <header className="border-b border-line px-3 py-3 lg:px-6">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-3 gap-y-2">
          <NavMenuButton />
          <div className="mr-auto flex min-w-0 flex-col">
            <h1 className="text-lg leading-6 font-semibold">Дашборд</h1>
            {dashboard.data && (
              <span className="text-xs text-fg-3">
                {formatRange(dashboard.data.date_from, dashboard.data.date_to)}
              </span>
            )}
          </div>
          <PeriodSwitch
            value={period}
            onChange={(next) => setSearch({ period: String(next) }, { replace: true })}
          />
        </div>
      </header>
      {body()}
    </section>
  )
}
