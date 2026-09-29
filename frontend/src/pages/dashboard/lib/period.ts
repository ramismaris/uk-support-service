import { PERIODS, type Period } from '../api/dashboard'

const DEFAULT_PERIOD: Period = 30

export function parsePeriod(raw: string | null): Period {
  return PERIODS.find((period) => String(period) === raw) ?? DEFAULT_PERIOD
}

const dayFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })

// The API sends calendar days ("2026-09-01"); `new Date(iso)` would read them as UTC midnight.
function localDay(iso: string): Date {
  const [year, month, day] = iso.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function formatDay(iso: string): string {
  return dayFormat.format(localDay(iso))
}

export function formatRange(from: string, to: string): string {
  return `${formatDay(from)} — ${formatDay(to)}`
}
