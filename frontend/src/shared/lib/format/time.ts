const MINUTE = 60_000
const HOUR = 60 * MINUTE

const timeFormat = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' })
const dayMonthFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })
const fullDateFormat = new Intl.DateTimeFormat('ru-RU', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function isYesterday(date: Date, now: Date): boolean {
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  return isSameDay(date, yesterday)
}

export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso)
  const diff = now.getTime() - date.getTime()
  if (diff < MINUTE) {
    return 'только что'
  }
  if (diff < HOUR) {
    return `${Math.floor(diff / MINUTE)} мин`
  }
  if (isSameDay(date, now)) {
    return timeFormat.format(date)
  }
  if (isYesterday(date, now)) {
    return 'вчера'
  }
  if (date.getFullYear() === now.getFullYear()) {
    return dayMonthFormat.format(date)
  }
  return fullDateFormat.format(date)
}

export function formatDateTime(iso: string, now: Date = new Date()): string {
  const date = new Date(iso)
  const time = timeFormat.format(date)
  return isSameDay(date, now) ? time : `${dayMonthFormat.format(date)}, ${time}`
}

// Time only: the day is shown once, above the day's messages (like Telegram).
export function formatTime(iso: string): string {
  return timeFormat.format(new Date(iso))
}

const dayLongFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' })

export function formatDayLabel(iso: string, now: Date = new Date()): string {
  const date = new Date(iso)
  if (isSameDay(date, now)) {
    return 'Сегодня'
  }
  if (isYesterday(date, now)) {
    return 'Вчера'
  }
  const day = dayLongFormat.format(date)
  return date.getFullYear() === now.getFullYear() ? day : `${day} ${date.getFullYear()}`
}

// The local calendar day, for grouping messages by it.
export function dayKey(iso: string): string {
  const date = new Date(iso)
  return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`
}
