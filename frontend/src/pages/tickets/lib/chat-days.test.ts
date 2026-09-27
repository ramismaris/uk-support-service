import { describe, expect, it } from 'vitest'
import { groupByDay } from './chat-days'

const at = (day: number, hour: number) => new Date(2026, 8, day, hour, 0).toISOString()

describe('groupByDay', () => {
  it('splits a chat into days in order', () => {
    const items = [
      { key: 'a', at: at(25, 10) },
      { key: 'b', at: at(25, 18) },
      { key: 'c', at: at(26, 9) },
    ]
    const days = groupByDay(items)
    expect(days.map((day) => day.items.map((item) => item.key))).toEqual([['a', 'b'], ['c']])
    expect(days[0]!.at).toBe(at(25, 10))
  })

  it('gives nothing for an empty chat', () => {
    expect(groupByDay([])).toEqual([])
  })
})
