import { describe, expect, it } from 'vitest'
import { formatDay, formatRange, parsePeriod } from './period'

describe('parsePeriod', () => {
  it('reads a known period from the address', () => {
    expect(parsePeriod('7')).toBe(7)
    expect(parsePeriod('90')).toBe(90)
  })

  it('falls back to 30 days', () => {
    expect(parsePeriod(null)).toBe(30)
    expect(parsePeriod('14')).toBe(30)
    expect(parsePeriod('abc')).toBe(30)
  })
})

describe('formatDay', () => {
  it('shows a calendar day without shifting it by the time zone', () => {
    expect(formatDay('2026-09-01')).toBe('1 сент.')
  })
})

describe('formatRange', () => {
  it('names both ends of the period', () => {
    expect(formatRange('2026-08-31', '2026-09-29')).toBe('31 авг. — 29 сент.')
  })
})
