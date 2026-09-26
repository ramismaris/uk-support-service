import { api, unwrap } from '@/shared/api'

export function markRead(ticketId: number) {
  return unwrap(
    api.POST('/api/v1/staff/tickets/{ticket_id}/read', {
      params: { path: { ticket_id: ticketId } },
    }),
  )
}
