const BASE_DELAY = 1000
const MAX_DELAY = 30_000

export const CLOSE_UNAUTHORIZED = 4401
export const CLOSE_FORBIDDEN = 4403

export function reconnectDelay(attempt: number): number {
  return Math.min(BASE_DELAY * 2 ** attempt, MAX_DELAY)
}

export function shouldReconnect(code: number): boolean {
  return code !== CLOSE_UNAUTHORIZED && code !== CLOSE_FORBIDDEN
}
