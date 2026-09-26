import { QueryClient } from '@tanstack/react-query'
import { describe, expect, it } from 'vitest'
import type { Message } from '../model/types'
import { appendMessage } from './append-message'
import { messageKeys } from './keys'

const message = (id: number, ticketId = 1042): Message => ({
  id,
  ticket_id: ticketId,
  sender_type: 'CLIENT',
  author: null,
  text: `m${id}`,
  files: [],
  created_at: '2026-09-26T12:00:00Z',
})

describe('appendMessage', () => {
  it('appends to the cached chat of that ticket', () => {
    const queryClient = new QueryClient()
    queryClient.setQueryData(messageKeys.list(1042), [message(1)])
    appendMessage(queryClient, message(2))
    expect(queryClient.getQueryData<Message[]>(messageKeys.list(1042))?.map((m) => m.id)).toEqual([
      1, 2,
    ])
  })

  it('ignores a message that is already in the chat', () => {
    const queryClient = new QueryClient()
    queryClient.setQueryData(messageKeys.list(1042), [message(1), message(2)])
    appendMessage(queryClient, message(2))
    expect(queryClient.getQueryData<Message[]>(messageKeys.list(1042))).toHaveLength(2)
  })

  it('does nothing when the chat is not loaded', () => {
    const queryClient = new QueryClient()
    appendMessage(queryClient, message(1, 7))
    expect(queryClient.getQueryData(messageKeys.list(7))).toBeUndefined()
  })
})
