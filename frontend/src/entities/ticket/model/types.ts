import type { components } from '@/shared/api'

export type TicketListItem = components['schemas']['TicketListItemResponse']
export type TicketDetail = components['schemas']['TicketDetailResponse']
export type TicketStatus = components['schemas']['TicketStatus']
export type TicketType = components['schemas']['TicketType']
export type ActiveTicketStatus = 'NEW' | 'IN_PROGRESS' | 'WAITING_CLIENT'

export interface TicketFilters {
  status: ActiveTicketStatus | null
  mine: boolean
}

export interface TicketPage {
  total: number
  items: TicketListItem[]
}
