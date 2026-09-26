import { create } from 'zustand'

export const CLOSE_UNDO_MS = 5000

interface PendingCloseState {
  ticketId: number | null
  // Set when the delayed request fails, so the toast can say so.
  error: string | null
  schedule: (ticketId: number, commit: () => void) => void
  cancel: () => void
  fail: (message: string | null) => void
}

let timer: ReturnType<typeof setTimeout> | undefined
let pendingCommit: (() => void) | null = null

// Closing is routine and managers cannot reopen, so the request waits out an undo window.
// Lives outside components: leaving the ticket must not cancel or lose the close.
export const usePendingClose = create<PendingCloseState>()((set) => {
  const clear = () => {
    clearTimeout(timer)
    pendingCommit = null
    set({ ticketId: null })
  }

  return {
    ticketId: null,
    error: null,
    schedule: (ticketId, commit) => {
      if (pendingCommit) {
        const previous = pendingCommit
        clear()
        previous()
      }
      pendingCommit = commit
      set({ ticketId, error: null })
      timer = setTimeout(() => {
        const run = pendingCommit
        clear()
        run?.()
      }, CLOSE_UNDO_MS)
    },
    cancel: clear,
    fail: (error) => set({ error }),
  }
})
