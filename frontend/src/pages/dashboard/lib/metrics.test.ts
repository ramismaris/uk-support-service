import { describe, expect, it } from 'vitest'
import { compare, formatDuration, formatRating, formatShare, previousNote } from './metrics'

describe('formatDuration', () => {
  it.each([
    [null, '—'],
    [0.2, '12 мин'],
    [0.99, '59 мин'],
    [1, '1 ч'],
    [5.25, '5,3 ч'],
    [47.9, '47,9 ч'],
    [48, '2 дн'],
    [80.4, '3,4 дн'],
  ])('%s h → %s', (hours, text) => {
    expect(formatDuration(hours)).toBe(text)
  })
})

describe('formatShare', () => {
  it('shows a share as whole percent', () => {
    expect(formatShare(0.873)).toBe('87%')
    expect(formatShare(1)).toBe('100%')
    expect(formatShare(null)).toBe('—')
  })
})

describe('formatRating', () => {
  it('keeps one decimal', () => {
    expect(formatRating(4.56)).toBe('4,6')
    expect(formatRating(5)).toBe('5,0')
    expect(formatRating(null)).toBe('—')
  })
})

describe('compare', () => {
  it('shows a relative change for counts and times', () => {
    expect(compare({ value: 120, previous: 100 }, 'percent', 'up')).toEqual({
      text: '+20%',
      tone: 'good',
    })
    expect(compare({ value: 3, previous: 4 }, 'percent', 'down')).toEqual({
      text: '−25%',
      tone: 'good',
    })
    expect(compare({ value: 6, previous: 4 }, 'percent', 'down')).toEqual({
      text: '+50%',
      tone: 'bad',
    })
  })

  it('shows percentage points for shares', () => {
    expect(compare({ value: 0.9, previous: 0.85 }, 'points', 'up')).toEqual({
      text: '+5 п.п.',
      tone: 'good',
    })
  })

  it('shows the plain difference for ratings', () => {
    expect(compare({ value: 4.2, previous: 4.5 }, 'difference', 'up')).toEqual({
      text: '−0,3',
      tone: 'bad',
    })
  })

  it('stays neutral when nothing changed', () => {
    expect(compare({ value: 10, previous: 10 }, 'percent', 'up')).toEqual({
      text: '0%',
      tone: 'neutral',
    })
  })

  it('treats a rounding-level change as no change', () => {
    expect(compare({ value: 0.901, previous: 0.9 }, 'points', 'up')).toEqual({
      text: '0 п.п.',
      tone: 'neutral',
    })
  })

  it('has nothing to compare with an empty side', () => {
    expect(compare({ value: 5, previous: 0 }, 'percent', 'up')).toBeNull()
    expect(compare({ value: null, previous: 3 }, 'percent', 'down')).toBeNull()
    expect(compare({ value: 3, previous: null }, 'points', 'up')).toBeNull()
  })
})

describe('previousNote', () => {
  it('names the previous value', () => {
    expect(previousNote(0.5, formatShare)).toBe('Было 50%')
    expect(previousNote(0, String)).toBe('Было 0')
  })

  it('says nothing when the previous period had no data', () => {
    expect(previousNote(null, formatShare)).toBeUndefined()
  })
})
