import { describe, expect, it } from 'vitest'
import { stepIndex, swipeAction } from './photo-viewer'

describe('swipeAction', () => {
  it('goes to the next photo on a swipe left and to the previous on a swipe right', () => {
    expect(swipeAction({ x: -120, y: 10 })).toBe('next')
    expect(swipeAction({ x: 120, y: -10 })).toBe('prev')
  })

  it('closes on a vertical swipe either way', () => {
    expect(swipeAction({ x: 20, y: 160 })).toBe('close')
    expect(swipeAction({ x: -20, y: -160 })).toBe('close')
  })

  it('ignores a short drag', () => {
    expect(swipeAction({ x: 40, y: 30 })).toBeNull()
  })

  it('follows the dominant direction of a diagonal drag', () => {
    expect(swipeAction({ x: -150, y: 130 })).toBe('next')
    expect(swipeAction({ x: 90, y: 200 })).toBe('close')
  })
})

describe('stepIndex', () => {
  it('moves within the photos', () => {
    expect(stepIndex(2, 1, 5)).toBe(3)
    expect(stepIndex(2, -1, 5)).toBe(1)
  })

  it('stops at the ends instead of wrapping', () => {
    expect(stepIndex(4, 1, 5)).toBe(4)
    expect(stepIndex(0, -1, 5)).toBe(0)
  })
})
