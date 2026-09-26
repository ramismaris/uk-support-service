import { describe, expect, it, vi } from 'vitest'
import { completionFallbackDelay, once } from './completion'

describe('completionFallbackDelay', () => {
  it('completes right away when motion is reduced and nothing plays', () => {
    expect(completionFallbackDelay(true, 3000)).toBe(0)
  })

  it('waits for the safety timeout otherwise', () => {
    expect(completionFallbackDelay(false, 3000)).toBe(3000)
  })
})

describe('once', () => {
  it('calls the handler only for the first of the complete event and the fallback', () => {
    const handler = vi.fn()
    const fire = once(handler)
    fire()
    fire()
    expect(handler).toHaveBeenCalledOnce()
  })
})
