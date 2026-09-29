import { describe, expect, it } from 'vitest'
import { sparklinePath } from './sparkline'

describe('sparklinePath', () => {
  it('spreads the points over the width and puts the peak at the top', () => {
    expect(sparklinePath([0, 2, 1], 100, 20)).toBe('M0,20 L50,0 L100,10')
  })

  it('keeps a flat series on the bottom line', () => {
    expect(sparklinePath([0, 0, 0], 100, 20)).toBe('M0,20 L50,20 L100,20')
  })

  it('draws a single day as a flat line across', () => {
    expect(sparklinePath([3], 100, 20)).toBe('M0,0 L100,0')
  })

  it('draws nothing without data', () => {
    expect(sparklinePath([], 100, 20)).toBe('')
  })
})
