import {
  CartesianGrid,
  Line,
  LineChart,
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
    <div className="rounded-xl bg-layer px-3 py-2 text-sm shadow-lg ring-1 ring-line">
      <div className="mb-1 font-medium">{formatDay(String(label))}</div>
      {SERIES.map((series) => (
        <div key={series.key} className="flex items-center gap-2 text-fg-2">
          <span className="h-0.5 w-3 rounded-full" style={{ backgroundColor: series.color }} />
          {series.label}
          <span className="ml-auto pl-4 font-medium text-fg tabular-nums">
            {payload.find((item) => item.dataKey === series.key)?.value}
          </span>
        </div>
      ))}
    </div>
  )
}

const axisTick = { fill: 'var(--text-tertiary)', fontSize: 12 }

// Lines rather than columns: 90 days of paired columns would be a few pixels each.
export default function DailyChart({ days }: { days: DashboardDay[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={days} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
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
        <YAxis allowDecimals={false} tick={axisTick} tickLine={false} axisLine={false} width={48} />
        <Tooltip
          content={ChartTooltip}
          cursor={{ stroke: 'var(--text-tertiary)', strokeWidth: 1 }}
          isAnimationActive={false}
        />
        {SERIES.map((series) => (
          <Line
            key={series.key}
            dataKey={series.key}
            name={series.label}
            type="linear"
            stroke={series.color}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            dot={false}
            activeDot={{
              r: 4,
              fill: series.color,
              stroke: 'var(--background-primary)',
              strokeWidth: 2,
            }}
            animationDuration={400}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
