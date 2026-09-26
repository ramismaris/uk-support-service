import type { ActiveTicketStatus, TicketFilters } from '@/entities/ticket'

const ACTIVE_STATUSES: readonly ActiveTicketStatus[] = ['NEW', 'IN_PROGRESS', 'WAITING_CLIENT']

function isActiveStatus(value: string | null): value is ActiveTicketStatus {
  return ACTIVE_STATUSES.includes(value as ActiveTicketStatus)
}

export function parseTicketFilters(search: URLSearchParams): TicketFilters {
  const status = search.get('status')
  return {
    status: isActiveStatus(status) ? status : null,
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
