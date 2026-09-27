import { describe, expect, it } from 'vitest'
import { albumLayout } from './album'

describe('albumLayout', () => {
  it('shows one photo on its own', () => {
    expect(albumLayout(1)).toEqual({ columns: 1, cells: [{ index: 0, rowSpan: 1 }], hidden: 0 })
  })

  it('puts two photos side by side', () => {
    expect(albumLayout(2)).toEqual({
      columns: 2,
      cells: [
        { index: 0, rowSpan: 1 },
        { index: 1, rowSpan: 1 },
      ],
      hidden: 0,
    })
  })

  it('makes the first of three photos tall, the other two stacked beside it', () => {
    expect(albumLayout(3)).toEqual({
      columns: 2,
      cells: [
        { index: 0, rowSpan: 2 },
        { index: 1, rowSpan: 1 },
        { index: 2, rowSpan: 1 },
      ],
      hidden: 0,
    })
  })

  it('shows four photos as a 2×2 grid', () => {
    expect(albumLayout(4).cells).toHaveLength(4)
    expect(albumLayout(4).hidden).toBe(0)
  })

  it('shows the first four of a bigger album and counts the rest', () => {
    const layout = albumLayout(10)
    expect(layout.cells.map((cell) => cell.index)).toEqual([0, 1, 2, 3])
    expect(layout.hidden).toBe(6)
  })

  it('has nothing to show without photos', () => {
    expect(albumLayout(0)).toEqual({ columns: 1, cells: [], hidden: 0 })
  })
})
