import type { Insights } from '../api/dashboard'

export type InsightsView = 'hidden' | 'items' | 'empty' | 'unavailable'

export function insightsView(data: Insights | undefined, failed: boolean): InsightsView {
  if (data?.status === 'disabled') {
    return 'hidden'
  }
  if (data?.status === 'ok') {
    return data.items.length > 0 ? 'items' : 'empty'
  }
  return failed || data?.status === 'unavailable' ? 'unavailable' : 'hidden'
}
