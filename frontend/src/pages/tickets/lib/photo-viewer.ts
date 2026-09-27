export type SwipeAction = 'prev' | 'next' | 'close'

const SWIPE_X = 80
const SWIPE_Y = 120

// A drag in the photo viewer: sideways flips photos, up or down closes (like Telegram).
export function swipeAction(offset: { x: number; y: number }): SwipeAction | null {
  const horizontal = Math.abs(offset.x) >= Math.abs(offset.y)
  if (horizontal && Math.abs(offset.x) >= SWIPE_X) {
    return offset.x < 0 ? 'next' : 'prev'
  }
  if (!horizontal && Math.abs(offset.y) >= SWIPE_Y) {
    return 'close'
  }
  return null
}

// No wrapping: the first and the last photo are ends, as in a chat.
export function stepIndex(index: number, delta: number, length: number): number {
  return Math.min(Math.max(index + delta, 0), length - 1)
}
