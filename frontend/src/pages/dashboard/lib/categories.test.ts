import { describe, expect, it } from 'vitest'
import { categoryRows } from './categories'

const category = (id: number, created: number, hours: number | null) => ({
  category_id: id,
  title: `Категория ${id}`,
  created,
  resolution_hours: hours,
})

describe('categoryRows', () => {
  it('gives each category its share of all requests', () => {
    const rows = categoryRows([category(1, 3, null), category(2, 1, null)], 72)
    expect(rows.map((row) => row.share)).toEqual([0.75, 0.25])
  })

  it('keeps the order of the backend', () => {
    const rows = categoryRows([category(2, 5, null), category(1, 1, null)], 72)
    expect(rows.map((row) => row.id)).toEqual([2, 1])
  })

  it('marks a category slow only when it takes longer than the norm', () => {
    const rows = categoryRows(
      [category(1, 1, 80), category(2, 1, 72), category(3, 1, 10), category(4, 1, null)],
      72,
    )
    expect(rows.map((row) => row.slow)).toEqual([true, false, false, false])
  })

  it('has no shares when nothing was created', () => {
    const rows = categoryRows([category(1, 0, 5)], 72)
    expect(rows[0].share).toBe(0)
  })

  it('returns nothing for no categories', () => {
    expect(categoryRows([], 72)).toEqual([])
  })
})
