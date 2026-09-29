import { motion, useReducedMotion } from 'framer-motion'
import { Info, Lightbulb, RefreshCw, Sparkles, TriangleAlert, type LucideIcon } from 'lucide-react'
import { formatTime } from '@/shared/lib/format'
import { Card } from '@/shared/ui/card'
import type { InsightItem, Period } from '../api/dashboard'
import { insightsView } from '../lib/insights'
import { useInsights, useRefreshInsights } from '../model/use-insights'

const KINDS: Record<InsightItem['kind'], { icon: LucideIcon; style: string }> = {
  fact: { icon: Info, style: 'text-brand' },
  observation: { icon: Lightbulb, style: 'text-fg-2' },
  warning: { icon: TriangleAlert, style: 'text-negative' },
}

export function InsightsCard({ period }: { period: Period }) {
  const reduceMotion = useReducedMotion()
  const insights = useInsights(period)
  const refresh = useRefreshInsights(period)
  const view = insightsView(insights.data, insights.isError)

  if (!insights.isPending && view === 'hidden') {
    return null
  }

  const generatedAt = insights.data?.generated_at
  const aside = (
    <span className="flex items-center gap-3">
      {generatedAt && view === 'items' && <span>Обновлено {formatTime(generatedAt)}</span>}
      <button
        type="button"
        disabled={refresh.isPending || insights.isPending}
        onClick={() => refresh.mutate()}
        className="flex items-center gap-1 font-medium text-brand hover:underline disabled:opacity-50"
      >
        <RefreshCw
          size={14}
          strokeWidth={2.25}
          aria-hidden="true"
          className={refresh.isPending ? 'animate-spin' : ''}
        />
        Обновить
      </button>
    </span>
  )

  const body = () => {
    if (insights.isPending) {
      return (
        <div aria-busy="true" className="flex flex-col gap-3">
          {['w-11/12', 'w-4/5', 'w-2/3'].map((width) => (
            <div key={width} className={`h-4 animate-pulse rounded bg-fill ${width}`} />
          ))}
        </div>
      )
    }
    if (view === 'unavailable') {
      return (
        <p className="text-sm text-fg-3">Выводы сейчас недоступны — цифры ниже это не касается.</p>
      )
    }
    if (view === 'empty') {
      return <p className="text-sm text-fg-3">За период не было обращений — выводить нечего.</p>
    }
    return (
      <ul
        className={`flex flex-col gap-3 transition-opacity ${refresh.isPending ? 'opacity-60' : ''}`}
      >
        {insights.data?.items.map((item, index) => {
          const { icon: Icon, style } = KINDS[item.kind]
          return (
            <motion.li
              key={`${item.kind}-${item.text}`}
              className="flex gap-3 text-[15px] leading-5"
              initial={reduceMotion ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.06, ease: [0.22, 1, 0.36, 1] }}
            >
              <Icon
                size={18}
                strokeWidth={2}
                aria-hidden="true"
                className={`mt-0.5 shrink-0 ${style}`}
              />
              {item.text}
            </motion.li>
          )
        })}
      </ul>
    )
  }

  return (
    <Card title="Выводы ИИ" icon={Sparkles} aside={aside}>
      {body()}
      {refresh.isError && (
        <p role="alert" className="mt-3 text-sm text-negative">
          {refresh.error.message}
        </p>
      )}
    </Card>
  )
}
