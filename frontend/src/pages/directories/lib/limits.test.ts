import { describe, expect, it } from 'vitest'
import { ACTIVE_LIMIT, activeCount, atLimit } from './limits'

const items = (active: number, disabled = 0) => [
  ...Array.from({ length: active }, () => ({ active: true })),
  ...Array.from({ length: disabled }, () => ({ active: false })),
]

describe('activeCount', () => {
  it('counts only the enabled ones', () => {
    expect(activeCount(items(3, 4))).toBe(3)
    expect(activeCount([])).toBe(0)
  })
})

describe('atLimit', () => {
  it('is 29, the number of buttons the bot can show', () => {
    expect(ACTIVE_LIMIT).toBe(29)
  })

  it('stops at the limit and not before', () => {
    expect(atLimit(items(ACTIVE_LIMIT - 1))).toBe(false)
    expect(atLimit(items(ACTIVE_LIMIT))).toBe(true)
  })

  it('does not count the disabled ones', () => {
    expect(atLimit(items(ACTIVE_LIMIT - 1, 10))).toBe(false)
  })
})
