import type { TicketListItem } from '@/entities/ticket'

// The list sorts by creation, but what matters to a manager is when the resident last wrote.
export function lastActivityAt(
  ticket: Pick<TicketListItem, 'created_at' | 'last_client_message_at'>,
): string {
  const { created_at: created, last_client_message_at: lastMessage } = ticket
  return lastMessage && lastMessage > created ? lastMessage : created
}
