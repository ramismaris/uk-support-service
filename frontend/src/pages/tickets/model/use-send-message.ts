import { useMutation, useQueryClient } from '@tanstack/react-query'
import { appendMessage } from '@/entities/message'
import { sendMessage } from '../api/send-message'

export function useSendMessage(ticketId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ text, files }: { text: string; files: File[] }) =>
      sendMessage(ticketId, text, files),
    onSuccess: (message) => appendMessage(queryClient, message),
  })
}
