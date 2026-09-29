export type ChartMode = 'bars' | 'lines'

// A pair of bars with a gap needs about this much width per day to stay readable.
const DAY_WIDTH = 14
// The value axis on the right takes this much of the chart's width.
const AXIS_WIDTH = 32

export function chartMode(width: number, days: number): ChartMode {
  if (days === 0) {
    return 'bars'
  }
  return (width - AXIS_WIDTH) / days >= DAY_WIDTH ? 'bars' : 'lines'
}
