import { describe, expect, it } from 'vitest'
import { dayKey, formatDateTime, formatDayLabel, formatRelativeTime, formatTime } from './time'

// Local-time dates keep the tests independent of the machine's timezone.
const now = new Date(2026, 8, 26, 15, 30)
const iso = (...args: [number, number, number, number, number]) => new Date(...args).toISOString()

describe('formatRelativeTime', () => {
  it('says "только что" within a minute', () => {
    const halfMinuteAgo = new Date(2026, 8, 26, 15, 29, 30).toISOString()
    expect(formatRelativeTime(halfMinuteAgo, now)).toBe('только что')
  })

  it('counts minutes within an hour', () => {
    expect(formatRelativeTime(iso(2026, 8, 26, 15, 5), now)).toBe('25 мин')
  })

  it('shows the time earlier today', () => {
    expect(formatRelativeTime(iso(2026, 8, 26, 9, 7), now)).toBe('09:07')
  })

  it('says "вчера" for yesterday', () => {
    expect(formatRelativeTime(iso(2026, 8, 25, 23, 0), now)).toBe('вчера')
  })

  it('shows day and month for older dates this year', () => {
    expect(formatRelativeTime(iso(2026, 2, 3, 10, 0), now)).toBe('3 мар.')
  })

  it('adds the year for previous years', () => {
    expect(formatRelativeTime(iso(2025, 11, 31, 10, 0), now)).toBe('31 дек. 2025 г.')
  })
})

describe('formatDateTime', () => {
  it('shows only the time today', () => {
    expect(formatDateTime(iso(2026, 8, 26, 9, 7), now)).toBe('09:07')
  })

  it('shows day, month and time on other days', () => {
    expect(formatDateTime(iso(2026, 8, 20, 18, 45), now)).toBe('20 сент., 18:45')
  })
})

describe('formatTime', () => {
  it('shows hours and minutes only, as in a chat bubble', () => {
    expect(formatTime(iso(2026, 8, 20, 18, 45))).toBe('18:45')
  })
})

describe('formatDayLabel', () => {
  it('names today and yesterday', () => {
    expect(formatDayLabel(iso(2026, 8, 26, 1, 0), now)).toBe('Сегодня')
    expect(formatDayLabel(iso(2026, 8, 25, 23, 59), now)).toBe('Вчера')
  })

  it('shows the full day and month this year', () => {
    expect(formatDayLabel(iso(2026, 8, 20, 12, 0), now)).toBe('20 сентября')
  })

  it('adds the year for previous years', () => {
    expect(formatDayLabel(iso(2025, 11, 31, 12, 0), now)).toBe('31 декабря 2025')
  })
})

describe('dayKey', () => {
  it('is the same within a local day and differs across midnight', () => {
    expect(dayKey(iso(2026, 8, 26, 0, 1))).toBe(dayKey(iso(2026, 8, 26, 23, 59)))
    expect(dayKey(iso(2026, 8, 26, 23, 59))).not.toBe(dayKey(iso(2026, 8, 27, 0, 0)))
  })
})
