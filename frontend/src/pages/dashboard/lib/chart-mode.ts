export type ChartMode = 'bars' | 'lines'

const DAY_WIDTH = 14
const AXIS_WIDTH = 32

export function chartMode(width: number, days: number): ChartMode {
  if (days === 0) {
    return 'bars'
  }
  return (width - AXIS_WIDTH) / days >= DAY_WIDTH ? 'bars' : 'lines'
}
