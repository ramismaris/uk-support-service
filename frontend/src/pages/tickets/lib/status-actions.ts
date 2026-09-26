import type { TicketStatus } from '@/entities/ticket'

const REASON_LIMIT = 3000

export function statusActionLabel(from: TicketStatus, to: TicketStatus): string {
  switch (to) {
    case 'WAITING_CLIENT':
      return 'Запросить ответ жильца'
    case 'CLOSED':
      return 'Закрыть'
    case 'REJECTED':
      return 'Отклонить'
    case 'IN_PROGRESS':
      if (from === 'NEW') {
        return 'Взять в работу'
      }
      return from === 'CLOSED' || from === 'REJECTED' ? 'Переоткрыть' : 'Вернуть в работу'
    case 'NEW':
      return 'Вернуть в новые'
  }
}

// Order of preference for the single primary button; rejection is never primary.
const PRIMARY_ORDER: readonly TicketStatus[] = ['CLOSED', 'IN_PROGRESS']

export function primaryStatusAction(
  from: TicketStatus,
  allowed: readonly TicketStatus[],
): TicketStatus | null {
  if (from === 'NEW' && allowed.includes('IN_PROGRESS')) {
    return 'IN_PROGRESS'
  }
  return PRIMARY_ORDER.find((status) => allowed.includes(status)) ?? null
}

export function validateRejectReason(reason: string): string | null {
  if (reason.trim() === '') {
    return 'Укажите причину — её увидит жилец'
  }
  if (reason.length > REASON_LIMIT) {
    return `Причина длиннее ${REASON_LIMIT} символов`
  }
  return null
}
