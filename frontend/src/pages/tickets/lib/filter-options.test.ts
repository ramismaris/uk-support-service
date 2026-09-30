import { describe, expect, it } from 'vitest'
import { hasActiveFilters, selectOptions } from './filter-options'

const items = [
  { id: 1, label: 'ул. Ленина, 12' },
  { id: 2, label: 'пр-т Мира, 28' },
]

describe('selectOptions', () => {
  it('puts "all" first and then every item', () => {
    expect(selectOptions(items, null, 'Все дома', (id) => `Дом №${id}`)).toEqual([
      { value: null, label: 'Все дома' },
      { value: 1, label: 'ул. Ленина, 12' },
      { value: 2, label: 'пр-т Мира, 28' },
    ])
  })

  it('adds a stand-in for a chosen id that the list no longer has', () => {
    const options = selectOptions(items, 7, 'Все дома', (id) => `Дом №${id}`)
    expect(options.at(-1)).toEqual({ value: 7, label: 'Дом №7' })
    expect(options).toHaveLength(4)
  })

  it('adds nothing for a chosen id that is in the list', () => {
    expect(selectOptions(items, 2, 'Все дома', (id) => `Дом №${id}`)).toHaveLength(3)
  })

  it('works while the list is still loading', () => {
    expect(selectOptions([], 3, 'Все дома', (id) => `Дом №${id}`)).toEqual([
      { value: null, label: 'Все дома' },
      { value: 3, label: 'Дом №3' },
    ])
  })
})

describe('hasActiveFilters', () => {
  const none = { status: null, mine: false, buildingId: null, categoryId: null }

  it('is false for the list as it opens', () => {
    expect(hasActiveFilters(none)).toBe(false)
  })

  it.each([{ status: 'NEW' as const }, { mine: true }, { buildingId: 4 }, { categoryId: 2 }])(
    'is true with %j',
    (change) => {
      expect(hasActiveFilters({ ...none, ...change })).toBe(true)
    },
  )
})
