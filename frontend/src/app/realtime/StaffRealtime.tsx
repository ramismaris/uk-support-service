import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { appendMessage, invalidateAllMessages } from '@/entities/message'
import { useSessionStore } from '@/entities/session'
import { invalidateAllTickets, invalidateTicket, invalidateTicketLists } from '@/entities/ticket'
import { CLOSE_UNAUTHORIZED, createReconnectingSocket, useSocketStatus } from '@/shared/lib/ws'
import { planRealtimeUpdate } from './plan-realtime-update'

function socketUrl(token: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/api/v1/ws?token=${encodeURIComponent(token)}`
}

export function StaffRealtime() {
  const queryClient = useQueryClient()
  const token = useSessionStore((state) => state.token)

  useEffect(() => {
    if (token === null) {
      return
    }
    const { setOnline } = useSocketStatus.getState()

    const apply = (event: unknown) => {
      for (const action of planRealtimeUpdate(event)) {
        switch (action.type) {
          case 'append-message':
            appendMessage(queryClient, action.message)
            break
          case 'invalidate-lists':
            void invalidateTicketLists(queryClient)
            break
          case 'invalidate-ticket':
            void invalidateTicket(queryClient, action.ticketId)
            break
          case 'invalidate-all':
            void invalidateAllTickets(queryClient)
            void invalidateAllMessages(queryClient)
            break
        }
      }
    }

    const socket = createReconnectingSocket({
      url: () => socketUrl(token),
      onMessage: apply,
      onOpen: (isReconnect) => {
        setOnline(true)
        if (isReconnect) {
          apply({ type: 'reconnected' })
        }
      },
      onDrop: () => setOnline(false),
      onFatalClose: (code) => {
        if (code === CLOSE_UNAUTHORIZED) {
          // Same as a 401 from the REST api: the session is gone.
          useSessionStore.getState().clear()
          queryClient.clear()
        }
      },
    })

    return () => {
      socket.close()
      setOnline(true)
    }
  }, [token, queryClient])

  return null
}
