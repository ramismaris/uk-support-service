import type { Message } from '@/entities/message'
import type { TicketDetail } from '@/entities/ticket'

type StatusChange = TicketDetail['history'][number]

export type TimelineItem =
  | { kind: 'message'; key: string; at: string; message: Message }
  | {
      kind: 'event'
      key: string
      at: string
      text: string
      actor: string | null
      comment: string | null
    }

// Participles, not verbs: the actor's gender is unknown.
export function statusEventText(change: StatusChange): string {
  switch (change.to_status) {
    case 'NEW':
      return 'Обращение создано'
    case 'WAITING_CLIENT':
      return 'Запрошен ответ жильца'
    case 'CLOSED':
      return 'Закрыто'
    case 'REJECTED':
      return 'Отклонено'
    case 'IN_PROGRESS':
      if (change.from_status === 'WAITING_CLIENT') {
        return 'Жилец ответил — снова в работе'
      }
      if (change.from_status === 'CLOSED' || change.from_status === 'REJECTED') {
        return 'Переоткрыто'
      }
      return 'Взято в работу'
  }
}

// The bot tells the resident about every status change; staff see the event itself instead.
const BOT_STATUS_NOTICE = /Статус заявки №\d+/

function isBotStatusNotice(message: Message): boolean {
  return message.sender_type === 'SYSTEM' && BOT_STATUS_NOTICE.test(message.text ?? '')
}

export function buildTimeline(messages: Message[], history: StatusChange[]): TimelineItem[] {
  const items: TimelineItem[] = [
    ...messages
      .filter((message) => !isBotStatusNotice(message))
      .map((message) => ({
        kind: 'message' as const,
        key: `m${message.id}`,
        at: message.created_at,
        message,
      })),
    ...history.map((change, index) => ({
      kind: 'event' as const,
      key: `e${index}`,
      at: change.created_at,
      text: statusEventText(change),
      actor: change.changed_by?.first_name ?? null,
      comment: change.comment,
    })),
  ]
  return items.sort((a, b) => a.at.localeCompare(b.at))
}
