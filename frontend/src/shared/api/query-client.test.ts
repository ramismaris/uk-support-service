import { describe, expect, it } from 'vitest'
import { ApiError } from './errors'
import { shouldRetry } from './query-client'

describe('shouldRetry', () => {
  it.each([401, 403, 404, 422])('does not retry %i', (status) => {
    expect(shouldRetry(0, new ApiError(status, 'x'))).toBe(false)
  })

  it('retries server errors and network failures twice', () => {
    expect(shouldRetry(0, new ApiError(500, 'x'))).toBe(true)
    expect(shouldRetry(1, new TypeError('Failed to fetch'))).toBe(true)
    expect(shouldRetry(2, new TypeError('Failed to fetch'))).toBe(false)
  })
})
