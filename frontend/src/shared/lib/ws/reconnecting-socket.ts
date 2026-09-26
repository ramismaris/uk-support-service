import { reconnectDelay, shouldReconnect } from './backoff'

interface ReconnectingSocketOptions {
  url: () => string
  onMessage: (data: unknown) => void
  // isReconnect: events may have been missed while the socket was down.
  onOpen: (isReconnect: boolean) => void
  onDrop: () => void
  onFatalClose: (code: number) => void
}

export function createReconnectingSocket(options: ReconnectingSocketOptions): { close(): void } {
  let socket: WebSocket | null = null
  let attempt = 0
  let opened = false
  let stopped = false
  let timer: ReturnType<typeof setTimeout> | undefined

  const connect = () => {
    socket = new WebSocket(options.url())
    socket.onopen = () => {
      options.onOpen(opened)
      opened = true
      attempt = 0
    }
    socket.onmessage = (event) => {
      try {
        options.onMessage(JSON.parse(String(event.data)))
      } catch {
        // Not JSON: nothing the panel can act on.
      }
    }
    socket.onclose = (event) => {
      socket = null
      if (stopped) {
        return
      }
      if (!shouldReconnect(event.code)) {
        options.onFatalClose(event.code)
        return
      }
      options.onDrop()
      timer = setTimeout(connect, reconnectDelay(attempt))
      attempt += 1
    }
  }

  connect()

  return {
    close() {
      stopped = true
      clearTimeout(timer)
      socket?.close()
    },
  }
}
