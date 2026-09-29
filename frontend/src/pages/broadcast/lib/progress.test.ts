import { describe, expect, it } from 'vitest'
import { broadcastProgress, statusLabel } from './progress'

const counts = (total: number, delivered: number, failed: number) => ({
  recipients_total: total,
  delivered_count: delivered,
  failed_count: failed,
})

describe('broadcastProgress', () => {
  it('counts delivered and failed as handled', () => {
    expect(broadcastProgress(counts(200, 120, 20))).toEqual({ handled: 140, share: 0.7 })
  })

  it('starts at zero', () => {
    expect(broadcastProgress(counts(50, 0, 0))).toEqual({ handled: 0, share: 0 })
  })

  it('never goes past the whole', () => {
    expect(broadcastProgress(counts(10, 10, 3)).share).toBe(1)
  })

  it('has no share without recipients', () => {
    expect(broadcastProgress(counts(0, 0, 0)).share).toBe(0)
  })
})

describe('statusLabel', () => {
  it('names each status in Russian', () => {
    expect(statusLabel('SENDING')).toBe('Идёт отправка')
    expect(statusLabel('DONE')).toBe('Отправлена')
    expect(statusLabel('INTERRUPTED')).toBe('Прервана')
  })
})
