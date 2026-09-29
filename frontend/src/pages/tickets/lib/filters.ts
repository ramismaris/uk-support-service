import type { TicketFilters, TicketStatus } from '@/entities/ticket'

const FILTER_STATUSES: readonly TicketStatus[] = [
  'NEW',
  'IN_PROGRESS',
  'WAITING_CLIENT',
  'CLOSED',
  'REJECTED',
]

function isFilterStatus(value: string | null): value is TicketStatus {
  return FILTER_STATUSES.includes(value as TicketStatus)
}

export function parseTicketFilters(search: URLSearchParams): TicketFilters {
  const status = search.get('status')
  return {
    status: isFilterStatus(status) ? status : null,
    mine: search.get('mine') === '1',
  }
}

export function ticketFiltersToSearch(filters: TicketFilters): URLSearchParams {
  const search = new URLSearchParams()
  if (filters.status) {
    search.set('status', filters.status)
  }
  if (filters.mine) {
    search.set('mine', '1')
  }
  return search
}
