import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from 'recharts'
import type { DashboardDay } from '../api/dashboard'
import type { SeriesKey } from '../config/series'
import { formatDay } from '../lib/period'

// Every day in a quiet brand tint; the one under the pointer in full brand colour.
const BAR = 'color-mix(in srgb, var(--brand) 22%, transparent)'
const ACTIVE_BAR = 'var(--brand)'

function ChartTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) {
    return null
  }
  return (
    <div className="rounded-lg bg-fg px-2 py-1 text-xs font-medium text-layer shadow-lg">
      {formatDay(String(label))}: {payload[0]?.value}
    </div>
  )
}

const axisTick = { fill: 'var(--text-tertiary)', fontSize: 12 }

export default function DailyChart({ days, series }: { days: DashboardDay[]; series: SeriesKey }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={days} margin={{ top: 8, right: 0, bottom: 0, left: 0 }} barCategoryGap="20%">
        <CartesianGrid vertical={false} stroke="var(--background-tertiary)" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDay}
          tick={axisTick}
          tickLine={false}
          axisLine={false}
          minTickGap={24}
          interval="preserveStartEnd"
        />
        <YAxis
          orientation="right"
          allowDecimals={false}
          tick={axisTick}
          tickLine={false}
          axisLine={false}
          width={32}
        />
        <Tooltip content={ChartTooltip} cursor={false} isAnimationActive={false} />
        <Bar
          dataKey={series}
          fill={BAR}
          activeBar={{ fill: ACTIVE_BAR }}
          radius={[4, 4, 0, 0]}
          maxBarSize={32}
          animationDuration={500}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
