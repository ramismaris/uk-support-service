import { describe, expect, it } from 'vitest'
import { planRealtimeUpdate } from './plan-realtime-update'

const message = {
  id: 7,
  ticket_id: 1042,
  sender_type: 'CLIENT',
  author: null,
  text: 'Течёт',
  files: [],
  created_at: '2026-09-26T12:00:00Z',
}

describe('planRealtimeUpdate', () => {
  it('appends a new chat message', () => {
    expect(planRealtimeUpdate({ type: 'message_created', message })).toEqual([
      { type: 'append-message', message },
    ])
  })

  it('refreshes lists on a new ticket', () => {
    expect(planRealtimeUpdate({ type: 'ticket_created', ticket: { id: 1050 } })).toEqual([
      { type: 'invalidate-lists' },
    ])
  })

  it('refreshes lists and the card on a ticket update', () => {
    expect(planRealtimeUpdate({ type: 'ticket_updated', ticket: { id: 1042 } })).toEqual([
      { type: 'invalidate-lists' },
      { type: 'invalidate-ticket', ticketId: 1042 },
    ])
  })

  it('refreshes everything after a reconnect', () => {
    expect(planRealtimeUpdate({ type: 'reconnected' })).toEqual([{ type: 'invalidate-all' }])
  })

  it.each([
    null,
    'text',
    { type: 'unknown' },
    { type: 'message_created' },
    { type: 'message_created', message: { id: 'x', ticket_id: 1 } },
    { type: 'ticket_updated', ticket: {} },
  ])('ignores malformed event %j', (event) => {
    expect(planRealtimeUpdate(event)).toEqual([])
  })
})
