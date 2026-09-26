import type { TicketStatus, TicketType } from './types'

export const statusLabels: Record<TicketStatus, string> = {
  NEW: 'Новое',
  IN_PROGRESS: 'В работе',
  WAITING_CLIENT: 'Ждёт ответа',
  CLOSED: 'Закрыто',
  REJECTED: 'Отклонено',
}

export const statusTones: Record<TicketStatus, string> = {
  NEW: 'bg-brand/10 text-brand',
  IN_PROGRESS: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  WAITING_CLIENT: 'bg-violet-500/15 text-violet-700 dark:text-violet-300',
  CLOSED: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  REJECTED: 'bg-neutral-500/15 text-neutral-600 dark:text-neutral-400',
}

export const ticketTypeLabels: Record<TicketType, string> = {
  REQUEST: 'Заявка',
  QUESTION: 'Вопрос',
}
