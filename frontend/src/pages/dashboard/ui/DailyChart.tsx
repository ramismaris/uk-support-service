import { useState } from 'react'
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from 'recharts'
import type { DashboardDay } from '../api/dashboard'
import { SERIES } from '../config/series'
import { chartMode } from '../lib/chart-mode'
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

const activeDot = (color: string) => ({
  r: 4,
  fill: color,
  stroke: 'var(--background-primary)',
  strokeWidth: 2,
})

const [created, closed] = SERIES

// Bars while every day gets room for a pair of them; lines when the days are too many for the
// width (a phone, or 90 days), where the same bars would be a fence of hairlines.
export default function DailyChart({ days }: { days: DashboardDay[] }) {
  const [width, setWidth] = useState(0)
  const mode = width === 0 ? 'bars' : chartMode(width, days.length)

  return (
    <ResponsiveContainer width="100%" height={260} onResize={(next) => setWidth(next)}>
      <ComposedChart
        data={days}
        margin={{ top: 8, right: 0, bottom: 0, left: 0 }}
        barCategoryGap="20%"
        barGap={2}
        // Not focusable: tapping the chart must not draw a focus frame. The table below is the
        // keyboard and screen reader way to the same numbers.
        accessibilityLayer={false}
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
          cursor={
            mode === 'bars'
              ? { fill: 'var(--background-tertiary)', opacity: 0.6 }
              : { stroke: 'var(--text-tertiary)', strokeWidth: 1 }
          }
          isAnimationActive={false}
        />
        {mode === 'bars' ? (
          SERIES.map((series) => (
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
          ))
        ) : (
          <>
            <Area
              dataKey={created.key}
              name={created.label}
              type="linear"
              stroke={created.color}
              strokeWidth={2}
              fill={created.color}
              fillOpacity={0.1}
              activeDot={activeDot(created.color)}
              animationDuration={500}
            />
            <Line
              dataKey={closed.key}
              name={closed.label}
              type="linear"
              stroke={closed.color}
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              dot={false}
              activeDot={activeDot(closed.color)}
              animationDuration={500}
            />
          </>
        )}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
