import { Button } from '@maxhub/max-ui'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { ChartColumn, CircleCheck, Inbox, Tags, Timer } from 'lucide-react'
import { lazy, Suspense, useState } from 'react'
import { useSearchParams } from 'react-router'
import { EmptyState } from '@/shared/ui/empty-state'
import { NavMenuButton } from '@/widgets/app-shell'
import { PERIODS, type Dashboard, type Period } from '../api/dashboard'
import { SERIES, type SeriesKey } from '../config/series'
import { compare, formatDuration, formatRating, formatShare, previousNote } from '../lib/metrics'
import { formatDay, formatRange, parsePeriod } from '../lib/period'
import { useDashboard } from '../model/use-dashboard'
import { AnimatedNumber } from './AnimatedNumber'
import { Card } from './Card'
import { Categories } from './Categories'
import { Delta, Figure, Meter } from './Figure'
import { NowPanel } from './NowPanel'
import { Sparkline } from './Sparkline'
import { StatCard } from './StatCard'
import { Stars } from './Stars'

// Recharts is heavy: only the admin opening the dashboard downloads it.
const DailyChart = lazy(() => import('./DailyChart'))

const count = (value: number) => String(Math.round(value))
const minutesAsDuration = (minutes: number) => formatDuration(minutes / 60)

// The cards come in one after another when the dashboard opens.
const stagger: Variants = { shown: { transition: { staggerChildren: 0.06 } } }

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

function SeriesSwitch({
  value,
  onChange,
}: {
  value: SeriesKey
  onChange: (series: SeriesKey) => void
}) {
  return (
    <div role="radiogroup" aria-label="Что показывать" className="flex rounded-lg bg-fill p-0.5">
      {SERIES.map((series) => (
        <button
          key={series.key}
          type="button"
          role="radio"
          aria-checked={series.key === value}
          onClick={() => onChange(series.key)}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            series.key === value ? 'bg-layer text-fg shadow-sm' : 'text-fg-2 hover:text-fg'
          }`}
        >
          {series.label}
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

function DailyCard({ data }: { data: Dashboard }) {
  const [series, setSeries] = useState<SeriesKey>('created')
  const metric = data.summary[series]
  return (
    <Card
      title="Обращения по дням"
      icon={ChartColumn}
      aside={<SeriesSwitch value={series} onChange={setSeries} />}
      bodyClassName="gap-3"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-[32px] leading-9 font-semibold">
          <AnimatedNumber value={metric.value} format={count} />
        </span>
        {(() => {
          const comparison = compare(metric, 'percent', 'up')
          return comparison && <Delta comparison={comparison} />
        })()}
        <span className="text-xs text-fg-3">к прошлым {data.period_days} дням</span>
      </div>
      <div className="min-h-[260px]">
        <Suspense fallback={null}>
          <DailyChart days={data.daily} series={series} />
        </Suspense>
      </div>
      <DailyTable days={data.daily} />
    </Card>
  )
}

function DashboardBody({ data }: { data: Dashboard }) {
  const { summary, sla } = data
  const reduceMotion = useReducedMotion()
  const reaction = summary.reaction_minutes
  const createdByDay = data.daily.map((day) => day.created)
  const closedByDay = data.daily.map((day) => day.closed)

  return (
    <motion.div
      className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]"
      variants={stagger}
      initial={reduceMotion ? false : 'hidden'}
      animate="shown"
    >
      <NowPanel now={data.now} className="xl:order-last" />

      <div className="flex min-w-0 flex-col gap-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            title="Поступило"
            icon={Inbox}
            value={summary.created.value}
            format={count}
            comparison={compare(summary.created, 'percent', 'up')}
            note={previousNote(summary.created.previous, String)}
            chart={<Sparkline values={createdByDay} color="var(--brand)" />}
          />
          <StatCard
            title="Закрыто"
            icon={CircleCheck}
            value={summary.closed.value}
            format={count}
            comparison={compare(summary.closed, 'percent', 'up')}
            note={previousNote(summary.closed.previous, String)}
            chart={<Sparkline values={closedByDay} color="var(--icon-positive)" />}
          />
          <StatCard
            title="Реакция в срок"
            icon={Timer}
            value={summary.reaction_on_time.value}
            format={formatShare}
            comparison={compare(summary.reaction_on_time, 'points', 'up')}
            note={previousNote(summary.reaction_on_time.previous, formatShare)}
          >
            {summary.reaction_on_time.value !== null && (
              <Meter share={summary.reaction_on_time.value} />
            )}
          </StatCard>
        </div>

        <DailyCard data={data} />

        <Card
          title="Сроки и оценки"
          icon={Timer}
          aside={`Норма: реакция ${sla.reaction_hours} ч, решение ${sla.resolution_hours} ч`}
        >
          <div className="grid grid-cols-2 gap-x-4 gap-y-5 lg:grid-cols-4">
            <Figure
              label="Реакция в среднем"
              value={reaction.value}
              format={minutesAsDuration}
              comparison={compare(reaction, 'percent', 'down')}
              note={previousNote(reaction.previous, minutesAsDuration)}
            />
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
          </div>
        </Card>

        <Card title="По категориям" icon={Tags} aside="Поступило за период и среднее время решения">
          <Categories categories={data.categories} questions={data.questions} />
        </Card>
      </div>
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
        className={`w-full p-4 transition-opacity lg:p-6 ${
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
        <div className="flex w-full flex-wrap items-center gap-x-3 gap-y-2">
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
