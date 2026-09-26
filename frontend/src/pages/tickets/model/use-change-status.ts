import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  invalidateTicket,
  invalidateTicketLists,
  ticketKeys,
  type TicketStatus,
} from '@/entities/ticket'
import { changeStatus } from '../api/change-status'

export function useChangeStatus(ticketId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ status, comment }: { status: TicketStatus; comment: string | null }) =>
      changeStatus(ticketId, status, comment),
    onSuccess: (ticket) => {
      queryClient.setQueryData(ticketKeys.detail(ticketId), ticket)
      void invalidateTicketLists(queryClient)
    },
    // Someone else may have changed the ticket first: show the fresh state.
    onError: () => void invalidateTicket(queryClient, ticketId),
  })
}
