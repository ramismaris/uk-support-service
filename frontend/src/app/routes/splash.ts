import type { SessionState } from './session-state'

// A quick sign-in would only flash the splash: it stays at least this long.
export const SPLASH_MIN_MS = 500

export function shouldShowSplash(kind: SessionState['kind'], minElapsed: boolean): boolean {
  return kind === 'loading' || (kind === 'ready' && !minElapsed)
}
