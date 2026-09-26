import { useMutation } from '@tanstack/react-query'
import { useCallback, useRef } from 'react'
import { markRead } from '../api/mark-read'

const MIN_INTERVAL = 1000

export function useMarkRead(ticketId: number): () => void {
  const { mutate } = useMutation({ mutationFn: () => markRead(ticketId) })
  const lastSent = useRef(0)
  return useCallback(() => {
    const now = Date.now()
    if (now - lastSent.current < MIN_INTERVAL) {
      return
    }
    lastSent.current = now
    mutate()
  }, [mutate])
}
