import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CLOSE_UNDO_MS, usePendingClose } from './pending-close'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  usePendingClose.getState().cancel()
  vi.useRealTimers()
})

describe('pending close', () => {
  it('commits after the undo window', () => {
    const commit = vi.fn()
    usePendingClose.getState().schedule(1000, commit)
    expect(usePendingClose.getState().ticketId).toBe(1000)
    vi.advanceTimersByTime(CLOSE_UNDO_MS - 1)
    expect(commit).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1)
    expect(commit).toHaveBeenCalledOnce()
    expect(usePendingClose.getState().ticketId).toBeNull()
  })

  it('does nothing when undone', () => {
    const commit = vi.fn()
    usePendingClose.getState().schedule(1000, commit)
    usePendingClose.getState().cancel()
    vi.advanceTimersByTime(CLOSE_UNDO_MS)
    expect(commit).not.toHaveBeenCalled()
    expect(usePendingClose.getState().ticketId).toBeNull()
  })

  it('commits the previous close right away when another one starts', () => {
    const first = vi.fn()
    const second = vi.fn()
    usePendingClose.getState().schedule(1000, first)
    usePendingClose.getState().schedule(1001, second)
    expect(first).toHaveBeenCalledOnce()
    expect(usePendingClose.getState().ticketId).toBe(1001)
  })
})
