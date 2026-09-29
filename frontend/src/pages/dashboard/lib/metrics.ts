const EMPTY = '—'
const MINUS = '−'

const oneDecimal = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 })
const fixedDecimal = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

// Minutes under an hour, hours under two days, days after that.
export function formatDuration(hours: number | null): string {
  if (hours === null) {
    return EMPTY
  }
  if (hours < 1) {
    return `${Math.round(hours * 60)} мин`
  }
  if (hours < 48) {
    return `${oneDecimal.format(hours)} ч`
  }
  return `${oneDecimal.format(hours / 24)} дн`
}

export function formatShare(share: number | null): string {
  return share === null ? EMPTY : `${Math.round(share * 100)}%`
}

export function formatRating(rating: number | null): string {
  return rating === null ? EMPTY : fixedDecimal.format(rating)
}

export interface Metric {
  value: number | null
  previous: number | null
}

// percent — relative change; points — shares, in percentage points; difference — ratings.
export type CompareKind = 'percent' | 'points' | 'difference'
// Which direction is good: more closed tickets is good, a longer reaction is bad.
export type Better = 'up' | 'down'

export interface Comparison {
  text: string
  tone: 'good' | 'bad' | 'neutral'
}

function signed(change: number, text: string): string {
  if (change > 0) {
    return `+${text}`
  }
  return change < 0 ? `${MINUS}${text}` : text
}

export function compare(metric: Metric, kind: CompareKind, better: Better): Comparison | null {
  const { value, previous } = metric
  if (value === null || previous === null || (kind === 'percent' && previous === 0)) {
    return null
  }
  let change: number
  let text: string
  if (kind === 'percent') {
    change = Math.round(((value - previous) / previous) * 100)
    text = `${Math.abs(change)}%`
  } else if (kind === 'points') {
    change = Math.round((value - previous) * 100)
    text = `${Math.abs(change)} п.п.`
  } else {
    change = Math.round((value - previous) * 10) / 10
    text = oneDecimal.format(Math.abs(change))
  }
  const improved = better === 'up' ? change > 0 : change < 0
  return {
    text: signed(change, text),
    tone: change === 0 ? 'neutral' : improved ? 'good' : 'bad',
  }
}

// "Было …" under a figure; nothing when the previous period had no data to show.
export function previousNote(
  previous: number | null,
  format: (value: number) => string,
): string | undefined {
  return previous === null ? undefined : `Было ${format(previous)}`
}
