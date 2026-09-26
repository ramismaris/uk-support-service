import type { TicketStatus, TicketType } from './types'

export const statusLabels: Record<TicketStatus, string> = {
  NEW: 'Новое',
  IN_PROGRESS: 'В работе',
  WAITING_CLIENT: 'Ждёт ответа',
  CLOSED: 'Закрыто',
  REJECTED: 'Отклонено',
}

// Colour is information: only the dot is tinted, the label stays quiet.
export const statusDots: Record<TicketStatus, string> = {
  NEW: 'bg-brand',
  IN_PROGRESS: 'bg-attention',
  WAITING_CLIENT: 'bg-waiting',
  CLOSED: 'bg-positive',
  REJECTED: 'bg-quiet',
}

export const ticketTypeLabels: Record<TicketType, string> = {
  REQUEST: 'Заявка',
  QUESTION: 'Вопрос',
}
