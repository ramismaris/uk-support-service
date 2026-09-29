import { describe, expect, it } from 'vitest'
import { bullet } from './bullet'

describe('bullet', () => {
  it('keeps the value under the norm marker and reads as on time', () => {
    const result = bullet(2, 4)
    expect(result.fill).toBeCloseTo(0.4)
    expect(result.mark).toBeCloseTo(0.8)
    expect(result.over).toBe(false)
  })

  it('pushes the marker back when the value overshoots the norm', () => {
    const result = bullet(8, 4)
    expect(result.fill).toBeCloseTo(0.8)
    expect(result.mark).toBeCloseTo(0.4)
    expect(result.over).toBe(true)
  })

  it('counts exactly the norm as on time', () => {
    expect(bullet(4, 4).over).toBe(false)
  })

  it('draws an empty bar for zero', () => {
    expect(bullet(0, 4).fill).toBe(0)
  })
})
