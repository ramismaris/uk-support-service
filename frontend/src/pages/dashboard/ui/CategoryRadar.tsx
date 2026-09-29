import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
} from 'recharts'
import { splitCategoryTitle } from '../lib/category-title'
import type { CategoryRow } from '../lib/categories'
import { formatDuration } from '../lib/metrics'

interface Point {
  emoji: string | null
  name: string
  created: number
  share: number
  hours: number | null
}

// What recharts hands a custom tick; coordinates may come as strings.
interface TickProps {
  x?: string | number
  y?: string | number
  textAnchor?: string
  index?: number
}

const ANCHORS = ['start', 'middle', 'end'] as const

function RadarTooltip({ active, payload }: TooltipContentProps) {
  const point = payload?.[0]?.payload as Point | undefined
  if (!active || !point) {
    return null
  }
  return (
    <div className="rounded-lg bg-fg px-2.5 py-1.5 text-xs text-layer shadow-lg">
      <div className="mb-1 font-medium">
        {point.emoji} {point.name}
      </div>
      <div className="flex gap-3">
        Поступило
        <span className="ml-auto font-medium tabular-nums">
          {point.created} · {Math.round(point.share * 100)}%
        </span>
      </div>
      {point.hours !== null && (
        <div className="flex gap-3">
          Решают
          <span className="ml-auto font-medium tabular-nums">{formatDuration(point.hours)}</span>
        </div>
      )}
    </div>
  )
}

// A polygon with one corner per category: the farther a corner from the centre, the more requests.
export default function CategoryRadar({ rows }: { rows: CategoryRow[] }) {
  const points: Point[] = rows.map((row) => ({
    ...splitCategoryTitle(row.title),
    created: row.created,
    share: row.share,
    hours: row.hours,
  }))

  // The corners carry the emoji, the full name and numbers are in the tooltip: no cut-off words.
  const tick = ({ x = 0, y = 0, textAnchor, index = 0 }: TickProps) => {
    const point = points[index]
    return (
      <text
        x={x}
        y={y}
        textAnchor={ANCHORS.find((anchor) => anchor === textAnchor) ?? 'middle'}
        dominantBaseline="central"
        fontSize={point?.emoji ? 18 : 11}
        fill="var(--text-secondary)"
      >
        {point?.emoji ?? point?.name}
      </text>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart
        data={points}
        outerRadius="76%"
        margin={{ top: 8, right: 8, bottom: 8, left: 8 }}
        // Not focusable: a tap must not draw a focus frame; the list view has the same numbers.
        accessibilityLayer={false}
      >
        <PolarGrid stroke="var(--text-tertiary)" strokeOpacity={0.35} />
        <PolarAngleAxis dataKey="name" tick={tick} />
        <PolarRadiusAxis domain={[0, 'dataMax']} tick={false} axisLine={false} />
        <Tooltip content={RadarTooltip} isAnimationActive={false} />
        <Radar
          dataKey="created"
          stroke="var(--brand)"
          strokeWidth={2}
          strokeLinejoin="round"
          fill="var(--brand)"
          fillOpacity={0.22}
          dot={{
            r: 3,
            fill: 'var(--brand)',
            stroke: 'var(--background-primary)',
            strokeWidth: 1.5,
          }}
          activeDot={{
            r: 5,
            fill: 'var(--brand)',
            stroke: 'var(--background-primary)',
            strokeWidth: 2,
          }}
          animationDuration={600}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
