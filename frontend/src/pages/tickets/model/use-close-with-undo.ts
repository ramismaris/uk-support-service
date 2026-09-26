import { useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { invalidateTicket, invalidateTicketLists, ticketKeys } from '@/entities/ticket'
import { changeStatus } from '../api/change-status'
import { usePendingClose } from './pending-close'

export function useCloseWithUndo(ticketId: number): () => void {
  const queryClient = useQueryClient()
  const schedule = usePendingClose((state) => state.schedule)
  const fail = usePendingClose((state) => state.fail)

  return useCallback(() => {
    // Called after the undo window, possibly when this ticket is no longer on screen.
    const commit = async () => {
      try {
        const ticket = await changeStatus(ticketId, 'CLOSED', null)
        queryClient.setQueryData(ticketKeys.detail(ticketId), ticket)
        void invalidateTicketLists(queryClient)
      } catch (error) {
        fail(error instanceof Error ? error.message : 'Не удалось закрыть обращение')
        void invalidateTicket(queryClient, ticketId)
      }
    }
    schedule(ticketId, () => void commit())
  }, [fail, queryClient, schedule, ticketId])
}
