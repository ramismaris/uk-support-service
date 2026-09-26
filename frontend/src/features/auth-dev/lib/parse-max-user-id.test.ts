import { describe, expect, it } from 'vitest'
import { parseMaxUserId } from './parse-max-user-id'

describe('parseMaxUserId', () => {
  it('parses a positive integer, trimming spaces', () => {
    expect(parseMaxUserId(' 1000002 ')).toBe(1000002)
  })

  it.each(['', '   ', 'abc', '12a', '-5', '0', '1.5', '99999999999999999999'])(
    'rejects %j',
    (input) => {
      expect(parseMaxUserId(input)).toBeNull()
    },
  )
})
