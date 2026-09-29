import { describe, expect, it } from 'vitest'
import { shouldShowSplash, SPLASH_MIN_MS } from './splash'

describe('shouldShowSplash', () => {
  it('shows while the session loads, however long that takes', () => {
    expect(shouldShowSplash('loading', false)).toBe(true)
    expect(shouldShowSplash('loading', true)).toBe(true)
  })

  it('holds a ready session behind the splash until the minimum time has passed', () => {
    expect(shouldShowSplash('ready', false)).toBe(true)
    expect(shouldShowSplash('ready', true)).toBe(false)
  })

  it.each(['unauthenticated', 'blocked', 'error'] as const)(
    'never makes %s wait for the splash',
    (kind) => {
      expect(shouldShowSplash(kind, false)).toBe(false)
    },
  )

  it('keeps the minimum at half a second', () => {
    expect(SPLASH_MIN_MS).toBe(500)
  })
})
