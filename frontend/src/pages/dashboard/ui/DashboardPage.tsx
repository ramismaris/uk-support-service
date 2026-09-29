import { Button } from '@maxhub/max-ui'
import { ChartColumn, TriangleAlert } from 'lucide-react'
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
import { Figure } from './Figure'

// Recharts is heavy: only the admin opening the dashboard downloads it.
const DailyChart = lazy(() => import('./DailyChart'))

const CHART_HEIGHT = 'h-60'

function Panel({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4 rounded-2xl bg-layer p-4 ring-1 ring-line lg:p-5">
      <header className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
        <h2 className="font-semibold">{title}</h2>
        {hint && <span className="text-xs text-fg-3">{hint}</span>}
      </header>
      {children}
    </section>
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
          className={`rounded-[10px] px-3 py-1.5 text-sm font-medium transition-colors ${
            period === value ? 'bg-layer text-fg shadow-sm' : 'text-fg-2 hover:text-fg'
          }`}
        >
          {period} дн
        </button>
      ))}
    </div>
  )
}

function DashboardBody({ data }: { data: Dashboard }) {
  const { now, summary, sla } = data
  const hours = (value: number | null) => (value === null ? null : value / 60)

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Сейчас" hint="Открытые обращения">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Figure label="Новые" value={String(now.new)} />
          <Figure label="В работе" value={String(now.in_progress)} />
          <Figure label="Ждут жильца" value={String(now.waiting_client)} />
          <Figure
            label="Просрочено"
            value={String(now.overdue)}
            emphasis={now.overdue > 0 ? 'negative' : undefined}
            note={
              now.overdue > 0 ? (
                <span className="inline-flex items-center gap-1">
                  <TriangleAlert size={12} strokeWidth={2} className="text-negative" />
                  Вышли за норму
                </span>
              ) : (
                'Все в срок'
              )
            }
          />
        </div>
      </Panel>

      <Panel title="Нагрузка" hint={`К прошлым ${data.period_days} дням`}>
        <div className="grid grid-cols-2 gap-4">
          <Figure
            label="Поступило"
            value={String(summary.created.value)}
            comparison={compare(summary.created, 'percent', 'up')}
            note={previousNote(summary.created.previous, String)}
          />
          <Figure
            label="Закрыто"
            value={String(summary.closed.value)}
            comparison={compare(summary.closed, 'percent', 'up')}
            note={previousNote(summary.closed.previous, String)}
          />
        </div>
      </Panel>

      <Panel
        title="Сроки"
        hint={`Норма: реакция ${sla.reaction_hours} ч, решение ${sla.resolution_hours} ч`}
      >
        <div className="grid grid-cols-2 gap-4">
          <Figure
            label="Реакция в среднем"
            value={formatDuration(hours(summary.reaction_minutes.value))}
            comparison={compare(summary.reaction_minutes, 'percent', 'down')}
            note={previousNote(summary.reaction_minutes.previous, (minutes) =>
              formatDuration(minutes / 60),
            )}
          />
          <Figure
            label="Реакция в срок"
            value={formatShare(summary.reaction_on_time.value)}
            comparison={compare(summary.reaction_on_time, 'points', 'up')}
            note={previousNote(summary.reaction_on_time.previous, formatShare)}
          />
          <Figure
            label="Решение в среднем"
            value={formatDuration(summary.resolution_hours.value)}
            comparison={compare(summary.resolution_hours, 'percent', 'down')}
            note={previousNote(summary.resolution_hours.previous, formatDuration)}
          />
          <Figure
            label="Решено в срок"
            value={formatShare(summary.resolution_on_time.value)}
            comparison={compare(summary.resolution_on_time, 'points', 'up')}
            note={previousNote(summary.resolution_on_time.previous, formatShare)}
          />
        </div>
      </Panel>

      <Panel title="Оценки жильцов" hint="По закрытым за период">
        <Figure
          label="Средняя оценка из 5"
          value={formatRating(summary.rating.value)}
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
        />
      </Panel>

      <div className="lg:col-span-2">
        <Panel title="По дням">
          <ul className="-mt-2 flex flex-wrap gap-4 text-sm text-fg-2">
            {SERIES.map((series) => (
              <li key={series.key} className="flex items-center gap-2">
                <span
                  className="h-0.5 w-4 rounded-full"
                  style={{ backgroundColor: series.color }}
                />
                {series.label}
              </li>
            ))}
          </ul>
          <Suspense fallback={<div className={CHART_HEIGHT} />}>
            <DailyChart days={data.daily} />
          </Suspense>
          <details className="text-sm">
            <summary className="cursor-pointer text-fg-2 select-none hover:text-fg">
              Таблицей
            </summary>
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
                  {data.daily.toReversed().map((day) => (
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
        </Panel>
      </div>

      <div className="lg:col-span-2">
        <Panel title="По категориям" hint="Поступило за период и среднее время решения">
          <Categories categories={data.categories} questions={data.questions} />
        </Panel>
      </div>
    </div>
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
