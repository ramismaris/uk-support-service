import { describe, expect, it } from 'vitest'
import { reconnectDelay, shouldReconnect } from './backoff'

describe('reconnectDelay', () => {
  it.each([
    [0, 1000],
    [1, 2000],
    [3, 8000],
    [4, 16000],
    [5, 30000],
    [12, 30000],
  ])('attempt %i waits %i ms', (attempt, delay) => {
    expect(reconnectDelay(attempt)).toBe(delay)
  })
})

describe('shouldReconnect', () => {
  it('stops on auth rejections', () => {
    expect(shouldReconnect(4401)).toBe(false)
    expect(shouldReconnect(4403)).toBe(false)
  })

  it('reconnects on network drops and server restarts', () => {
    expect(shouldReconnect(1006)).toBe(true)
    expect(shouldReconnect(1012)).toBe(true)
  })
})
