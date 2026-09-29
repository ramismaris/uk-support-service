import { Button } from '@maxhub/max-ui'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { ChartColumn, ChevronRight, CircleCheck, Inbox, Star } from 'lucide-react'
import { lazy, Suspense, useId, useState } from 'react'
import { useSearchParams } from 'react-router'
import { EmptyState } from '@/shared/ui/empty-state'
import { NavMenuButton } from '@/widgets/app-shell'
import { PERIODS, type Dashboard, type Period } from '../api/dashboard'
import { SERIES } from '../config/series'
import { compare, formatRating, previousNote } from '../lib/metrics'
import { formatDay, formatRange, parsePeriod } from '../lib/period'
import { useDashboard } from '../model/use-dashboard'
import { Card } from './Card'
import { Categories } from './Categories'
import { NowPanel } from './NowPanel'
import { SlaCard } from './SlaCard'
import { Sparkline } from './Sparkline'
import { StatCard } from './StatCard'
import { Stars } from './Stars'

// Recharts is heavy: only the admin opening the dashboard downloads it.
const DailyChart = lazy(() => import('./DailyChart'))

const count = (value: number) => String(Math.round(value))

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

// The chart's numbers as a table. Opens by growing from zero height: a grid row going 0fr → 1fr.
function DailyTable({ days }: { days: Dashboard['daily'] }) {
  const [open, setOpen] = useState(false)
  const tableId = useId()
  return (
    <div className="text-sm">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={tableId}
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 text-fg-2 hover:text-fg"
      >
        <ChevronRight
          size={16}
          aria-hidden="true"
          className={`transition-transform duration-300 ease-out motion-reduce:transition-none ${open ? 'rotate-90' : ''}`}
        />
        Таблицей
      </button>
      <div
        id={tableId}
        inert={!open}
        className={`grid transition-[grid-template-rows,opacity] duration-300 ease-out motion-reduce:transition-none ${
          open ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
        }`}
      >
        <div className="min-h-0 overflow-hidden">
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
        </div>
      </div>
    </div>
  )
}

function DailyCard({ data }: { data: Dashboard }) {
  return (
    <Card title="Обращения по дням" icon={ChartColumn} bodyClassName="gap-3">
      {/* Two series need a key; the totals are in the cards above. */}
      <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-fg-2">
        {SERIES.map((series) => (
          <li key={series.key} className="flex items-center gap-2">
            <span className="size-2.5 rounded-sm" style={{ backgroundColor: series.color }} />
            {series.label}
          </li>
        ))}
      </ul>
      <div className="min-h-[260px]">
        <Suspense fallback={null}>
          <DailyChart days={data.daily} />
        </Suspense>
      </div>
      <DailyTable days={data.daily} />
    </Card>
  )
}

function ratingNote(rating: Dashboard['summary']['rating']): string {
  if (rating.count === 0) {
    return 'Оценок пока нет'
  }
  return [`Оценок: ${rating.count}`, previousNote(rating.previous, formatRating)]
    .filter(Boolean)
    .join('. ')
}

function DashboardBody({ data }: { data: Dashboard }) {
  const { summary } = data
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]"
      variants={stagger}
      initial={reduceMotion ? false : 'hidden'}
      animate="shown"
    >
      <NowPanel now={data.now} className="xl:col-start-2 xl:row-start-1" />

      <div className="flex min-w-0 flex-col gap-4 xl:col-start-1 xl:row-span-2 xl:row-start-1">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatCard
            title="Поступило"
            icon={Inbox}
            value={summary.created.value}
            format={count}
            comparison={compare(summary.created, 'percent', 'up')}
            note={previousNote(summary.created.previous, String)}
            chart={
              <Sparkline values={data.daily.map((day) => day.created)} color={SERIES[0].color} />
            }
          />
          <StatCard
            title="Закрыто"
            icon={CircleCheck}
            value={summary.closed.value}
            format={count}
            comparison={compare(summary.closed, 'percent', 'up')}
            note={previousNote(summary.closed.previous, String)}
            chart={
              <Sparkline values={data.daily.map((day) => day.closed)} color={SERIES[1].color} />
            }
          />
          <StatCard
            title="Оценка жильцов"
            icon={Star}
            value={summary.rating.value}
            format={formatRating}
            comparison={compare(summary.rating, 'difference', 'up')}
            note={ratingNote(summary.rating)}
          >
            {summary.rating.value !== null && <Stars rating={summary.rating.value} />}
          </StatCard>
        </div>

        <DailyCard data={data} />
        <SlaCard data={data} />
      </div>

      <Categories data={data} />
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
