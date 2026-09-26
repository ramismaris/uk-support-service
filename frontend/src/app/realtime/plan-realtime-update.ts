import type { Message } from '@/entities/message'

export type RealtimeAction =
  | { type: 'append-message'; message: Message }
  | { type: 'invalidate-lists' }
  | { type: 'invalidate-ticket'; ticketId: number }
  | { type: 'invalidate-all' }

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function ticketIdOf(event: Record<string, unknown>): number | null {
  const ticket = event.ticket
  return isObject(ticket) && typeof ticket.id === 'number' ? ticket.id : null
}

function isMessage(value: unknown): value is Message {
  return isObject(value) && typeof value.id === 'number' && typeof value.ticket_id === 'number'
}

// Events come from the network: anything unexpected is ignored rather than trusted.
export function planRealtimeUpdate(event: unknown): RealtimeAction[] {
  if (!isObject(event)) {
    return []
  }
  switch (event.type) {
    case 'message_created':
      return isMessage(event.message) ? [{ type: 'append-message', message: event.message }] : []
    case 'ticket_created':
      return ticketIdOf(event) !== null ? [{ type: 'invalidate-lists' }] : []
    case 'ticket_updated': {
      const ticketId = ticketIdOf(event)
      return ticketId !== null
        ? [{ type: 'invalidate-lists' }, { type: 'invalidate-ticket', ticketId }]
        : []
    }
    case 'reconnected':
      return [{ type: 'invalidate-all' }]
    default:
      return []
  }
}
