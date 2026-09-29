import { describe, expect, it } from 'vitest'
import { chartMode } from './chart-mode'

describe('chartMode', () => {
  it('uses bars while every day has room for a pair of them', () => {
    expect(chartMode(800, 30)).toBe('bars')
    expect(chartMode(300, 7)).toBe('bars')
  })

  it('switches to lines when the days are too many for the width', () => {
    expect(chartMode(300, 30)).toBe('lines')
    expect(chartMode(800, 90)).toBe('lines')
  })

  it('counts the width the plot really gets, without the axis', () => {
    expect(chartMode(452, 30)).toBe('bars')
    expect(chartMode(451, 30)).toBe('lines')
  })

  it('needs at least one day', () => {
    expect(chartMode(800, 0)).toBe('bars')
  })
})
