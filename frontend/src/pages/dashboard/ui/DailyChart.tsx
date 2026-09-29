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
import { SERIES } from '../config/series'
import { formatDay } from '../lib/period'

function ChartTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) {
    return null
  }
  return (
    <div className="rounded-lg bg-fg px-2.5 py-1.5 text-xs text-layer shadow-lg">
      <div className="mb-1 font-medium">{formatDay(String(label))}</div>
      {SERIES.map((series) => (
        <div key={series.key} className="flex items-center gap-2">
          <span className="size-2 rounded-sm" style={{ backgroundColor: series.color }} />
          {series.label}
          <span className="ml-auto pl-3 font-medium tabular-nums">
            {payload.find((item) => item.dataKey === series.key)?.value}
          </span>
        </div>
      ))}
    </div>
  )
}

const axisTick = { fill: 'var(--text-tertiary)', fontSize: 12 }

// Two series side by side on one axis: what came in and what was closed, day by day.
export default function DailyChart({ days }: { days: DashboardDay[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart
        data={days}
        margin={{ top: 8, right: 0, bottom: 0, left: 0 }}
        barCategoryGap="20%"
        barGap={2}
      >
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
        <Tooltip
          content={ChartTooltip}
          cursor={{ fill: 'var(--background-tertiary)', opacity: 0.6 }}
          isAnimationActive={false}
        />
        {SERIES.map((series) => (
          <Bar
            key={series.key}
            dataKey={series.key}
            name={series.label}
            // A tinted body with a solid outline: the bars stay readable even when they are thin.
            fill={`color-mix(in srgb, ${series.color} 22%, transparent)`}
            stroke={series.color}
            strokeWidth={1.5}
            radius={[3, 3, 0, 0]}
            maxBarSize={16}
            animationDuration={500}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
