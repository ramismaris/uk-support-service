import type { TicketStatus, TicketType } from './types'

export const statusLabels: Record<TicketStatus, string> = {
  NEW: 'Новое',
  IN_PROGRESS: 'В работе',
  WAITING_CLIENT: 'Ждём жильца',
  CLOSED: 'Закрыто',
  REJECTED: 'Отклонено',
}

// Each status has its own colour, readable on both themes; NEW takes the company's colour.
export const statusColors: Record<TicketStatus, string> = {
  NEW: 'text-brand',
  IN_PROGRESS: 'text-orange-600 dark:text-orange-400',
  WAITING_CLIENT: 'text-violet-600 dark:text-violet-400',
  CLOSED: 'text-emerald-600 dark:text-emerald-400',
  REJECTED: 'text-fg-3',
}

export const ticketTypeLabels: Record<TicketType, string> = {
  REQUEST: 'Заявка',
  QUESTION: 'Вопрос',
}
