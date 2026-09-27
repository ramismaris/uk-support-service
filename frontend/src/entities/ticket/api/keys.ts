import type { TicketFilters } from '../model/types'

export const ticketKeys = {
  all: ['tickets'] as const,
  lists: () => [...ticketKeys.all, 'list'] as const,
  list: (filters: TicketFilters) => [...ticketKeys.lists(), filters] as const,
  // Under lists: whatever refreshes the lists refreshes the count too.
  unreadCount: () => [...ticketKeys.lists(), 'unread-count'] as const,
  details: () => [...ticketKeys.all, 'detail'] as const,
  detail: (id: number) => [...ticketKeys.details(), id] as const,
}
