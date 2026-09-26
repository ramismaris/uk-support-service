import { useInfiniteQuery, useQuery, type QueryClient } from '@tanstack/react-query'
import { api, unwrap } from '@/shared/api'
import type { TicketFilters, TicketPage } from '../model/types'
import { ticketKeys } from './keys'

const PAGE_SIZE = 50

export function nextPageOffset(pages: TicketPage[]): number | undefined {
  const loaded = pages.reduce((count, page) => count + page.items.length, 0)
  const total = pages.at(-1)?.total ?? 0
  return loaded < total ? loaded : undefined
}

export function useTicketList(filters: TicketFilters) {
  return useInfiniteQuery({
    queryKey: ticketKeys.list(filters),
    queryFn: ({ pageParam }) =>
      unwrap(
        api.GET('/api/v1/staff/tickets', {
          params: {
            query: {
              status: filters.status ?? undefined,
              mine: filters.mine || undefined,
              skip: pageParam,
              limit: PAGE_SIZE,
            },
          },
        }),
      ),
    initialPageParam: 0,
    getNextPageParam: (_lastPage, pages) => nextPageOffset(pages),
  })
}

export function useTicket(id: number) {
  return useQuery({
    queryKey: ticketKeys.detail(id),
    queryFn: () =>
      unwrap(api.GET('/api/v1/staff/tickets/{ticket_id}', { params: { path: { ticket_id: id } } })),
  })
}

export function invalidateTicketLists(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
}

export function invalidateTicket(queryClient: QueryClient, id: number): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: ticketKeys.detail(id) })
}

export function invalidateAllTickets(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: ticketKeys.all })
}
