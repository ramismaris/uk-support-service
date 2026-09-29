import { describe, expect, it } from 'vitest'
import type { Insights } from '../api/dashboard'
import { insightsView } from './insights'

const response = (status: Insights['status'], count = 0): Insights => ({
  status,
  period_days: 30,
  generated_at: '2026-09-29T12:00:00Z',
  items: Array.from({ length: count }, (_, index) => ({
    kind: 'fact' as const,
    text: `Вывод ${index + 1}`,
  })),
})

describe('insightsView', () => {
  it('hides the block when the AI is switched off', () => {
    expect(insightsView(response('disabled'), false)).toBe('hidden')
  })

  it('shows the items of a good answer', () => {
    expect(insightsView(response('ok', 4), false)).toBe('items')
  })

  it('says there is nothing to tell when the answer has no items', () => {
    expect(insightsView(response('ok', 0), false)).toBe('empty')
  })

  it('offers a retry when the AI did not answer', () => {
    expect(insightsView(response('unavailable'), false)).toBe('unavailable')
  })

  it('treats a failed request like an AI that did not answer', () => {
    expect(insightsView(undefined, true)).toBe('unavailable')
  })

  it('keeps the shown items when only a refresh failed', () => {
    expect(insightsView(response('ok', 3), true)).toBe('items')
  })
})
