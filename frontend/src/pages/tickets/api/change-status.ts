import type { TicketStatus } from '@/entities/ticket'
import { api, unwrap } from '@/shared/api'

export function changeStatus(ticketId: number, status: TicketStatus, comment: string | null) {
  return unwrap(
    api.POST('/api/v1/staff/tickets/{ticket_id}/status', {
      params: { path: { ticket_id: ticketId } },
      body: { status, comment },
    }),
  )
}
