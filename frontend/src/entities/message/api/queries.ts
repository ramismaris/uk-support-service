import { useQuery, type QueryClient } from '@tanstack/react-query'
import { api, unwrap } from '@/shared/api'
import { messageKeys } from './keys'

export function useMessages(ticketId: number) {
  return useQuery({
    queryKey: messageKeys.list(ticketId),
    queryFn: () =>
      unwrap(
        api.GET('/api/v1/staff/tickets/{ticket_id}/messages', {
          params: { path: { ticket_id: ticketId } },
        }),
      ),
  })
}

export function invalidateAllMessages(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: messageKeys.all })
}
