import { describe, expect, it } from 'vitest'
import { centeredScrollLeft, scrollEdges } from './scroll-edges'

describe('centeredScrollLeft', () => {
  const at = (chipLeft: number, scrollLeft = 0) =>
    centeredScrollLeft({ scrollLeft, rowLeft: 0, rowWidth: 300, chipLeft, chipWidth: 100 })

  it('brings a chip from the right into the middle of the row', () => {
    expect(at(400)).toBe(300)
  })

  it('keeps the scroll position for a chip that is already in the middle', () => {
    expect(at(100, 50)).toBe(50)
  })

  it('counts the distance from the row, not from the page', () => {
    expect(
      centeredScrollLeft({
        scrollLeft: 0,
        rowLeft: 20,
        rowWidth: 300,
        chipLeft: 420,
        chipWidth: 100,
      }),
    ).toBe(300)
  })

  it('never asks for a position before the start', () => {
    expect(at(-80, 0)).toBe(0)
  })
})

const row = (scrollLeft: number, clientWidth: number, scrollWidth: number) => ({
  scrollLeft,
  clientWidth,
  scrollWidth,
})

describe('scrollEdges', () => {
  it('has more to see on the right at the start', () => {
    expect(scrollEdges(row(0, 300, 500))).toEqual({ start: false, end: true })
  })

  it('has more on both sides in the middle', () => {
    expect(scrollEdges(row(100, 300, 500))).toEqual({ start: true, end: true })
  })

  it('has more only on the left at the end', () => {
    expect(scrollEdges(row(200, 300, 500))).toEqual({ start: true, end: false })
  })

  it('has nothing hidden when everything fits', () => {
    expect(scrollEdges(row(0, 300, 300))).toEqual({ start: false, end: false })
  })

  it('ignores a sub-pixel remainder at the end', () => {
    expect(scrollEdges(row(199.5, 300, 500))).toEqual({ start: true, end: false })
  })
})
