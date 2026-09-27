import { describe, expect, it } from 'vitest'
import type { Message } from '@/entities/message'
import { firstUnreadMessageId } from './unread-divider'

const message = (id: number, sender_type: Message['sender_type']): Message => ({
  id,
  ticket_id: 1000,
  sender_type,
  author: null,
  text: 'Текст',
  files: [],
  created_at: '2026-09-26T10:01:00Z',
})

describe('firstUnreadMessageId', () => {
  it('points at the first resident message after the last staff reply', () => {
    const messages = [
      message(1, 'CLIENT'),
      message(2, 'STAFF'),
      message(3, 'CLIENT'),
      message(4, 'CLIENT'),
    ]
    expect(firstUnreadMessageId(messages, true)).toBe(3)
  })

  it('ignores bot messages between the reply and the new ones', () => {
    const messages = [message(1, 'STAFF'), message(2, 'SYSTEM'), message(3, 'CLIENT')]
    expect(firstUnreadMessageId(messages, true)).toBe(3)
  })

  it('takes the whole chat when nobody has answered yet', () => {
    expect(firstUnreadMessageId([message(1, 'CLIENT'), message(2, 'CLIENT')], true)).toBe(1)
  })

  it('shows no divider for a read ticket', () => {
    expect(firstUnreadMessageId([message(1, 'CLIENT')], false)).toBeNull()
  })
})
