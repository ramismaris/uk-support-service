import type { Message } from '@/entities/message'

// Where "Новые сообщения" goes: the resident messages that came after the last staff reply.
// The read mark is one per ticket, so this is an estimate — good enough to find the place.
export function firstUnreadMessageId(messages: Message[], unread: boolean): number | null {
  if (!unread) {
    return null
  }
  const lastReply = messages.findLastIndex((message) => message.sender_type === 'STAFF')
  const first = messages.slice(lastReply + 1).find((message) => message.sender_type === 'CLIENT')
  return first?.id ?? null
}
