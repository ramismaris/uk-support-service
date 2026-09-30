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

function parseId(value: string | null): number | null {
  if (value === null || !/^[1-9]\d*$/.test(value)) {
    return null
  }
  const id = Number(value)
  return Number.isSafeInteger(id) ? id : null
}

export function parseTicketFilters(search: URLSearchParams): TicketFilters {
  const status = search.get('status')
  return {
    status: isFilterStatus(status) ? status : null,
    mine: search.get('mine') === '1',
    buildingId: parseId(search.get('building')),
    categoryId: parseId(search.get('category')),
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
  if (filters.buildingId !== null) {
    search.set('building', String(filters.buildingId))
  }
  if (filters.categoryId !== null) {
    search.set('category', String(filters.categoryId))
  }
  return search
}
