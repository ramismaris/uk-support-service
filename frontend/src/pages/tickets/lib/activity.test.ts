import { describe, expect, it } from 'vitest'
import { lastActivityAt } from './activity'

describe('lastActivityAt', () => {
  it('uses the latest resident message when there is one', () => {
    expect(
      lastActivityAt({
        created_at: '2026-09-25T10:00:00Z',
        last_client_message_at: '2026-09-26T09:00:00Z',
      }),
    ).toBe('2026-09-26T09:00:00Z')
  })

  it('falls back to creation time', () => {
    expect(
      lastActivityAt({ created_at: '2026-09-25T10:00:00Z', last_client_message_at: null }),
    ).toBe('2026-09-25T10:00:00Z')
  })
})
