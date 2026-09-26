import { describe, expect, it } from 'vitest'
import { ticketPathFromStartParam } from './deep-link'

describe('ticketPathFromStartParam', () => {
  it('opens the ticket from the "Открыть" button', () => {
    expect(ticketPathFromStartParam('ticket_1042')).toBe('/staff/tickets/1042')
  })

  it.each([
    null,
    '',
    'ticket_',
    'ticket_abc',
    'ticket_-1',
    'ticket_0',
    'ticket_1.5',
    'foo',
    'ticket_12x',
  ])('ignores %j', (param) => {
    expect(ticketPathFromStartParam(param)).toBeNull()
  })
})
