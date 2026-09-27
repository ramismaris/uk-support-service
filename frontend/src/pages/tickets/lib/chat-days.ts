import { dayKey } from '@/shared/lib/format'

export interface ChatDay<T> {
  key: string
  // The first item's time, to label the day.
  at: string
  items: T[]
}

// Items come in chat order; each local day gets its own group under a date separator.
export function groupByDay<T extends { at: string }>(items: T[]): ChatDay<T>[] {
  const days: ChatDay<T>[] = []
  for (const item of items) {
    const key = dayKey(item.at)
    const last = days.at(-1)
    if (last?.key === key) {
      last.items.push(item)
    } else {
      days.push({ key, at: item.at, items: [item] })
    }
  }
  return days
}
