import type { QueryClient } from '@tanstack/react-query'
import type { Message } from '../model/types'
import { messageKeys } from './keys'

// A sent message comes back twice: in the POST response and as a message_created event.
export function appendMessage(queryClient: QueryClient, message: Message): void {
  queryClient.setQueryData<Message[]>(messageKeys.list(message.ticket_id), (messages) => {
    if (!messages || messages.some((existing) => existing.id === message.id)) {
      return messages
    }
    return [...messages, message]
  })
}
