import { describe, expect, it } from 'vitest'
import { contrastWithWhite, LOW_CONTRAST } from './contrast'

describe('contrastWithWhite', () => {
  it('is 21 for black and 1 for white', () => {
    expect(contrastWithWhite('#000000')).toBeCloseTo(21, 1)
    expect(contrastWithWhite('#ffffff')).toBeCloseTo(1, 5)
  })

  it('passes Max blue and fails a pale yellow', () => {
    expect(contrastWithWhite('#007aff')).toBeGreaterThanOrEqual(LOW_CONTRAST)
    expect(contrastWithWhite('#ffe066')).toBeLessThan(LOW_CONTRAST)
  })
})
