// A tab opened before a deploy still asks for the old hashed chunks, which the new build no
// longer has. Vite reports that as `vite:preloadError`; reloading picks up the new build.

export const RELOAD_GUARD_MS = 10_000

const STORAGE_KEY = 'uk-stale-build-reload'

// One reload per guard window: if the chunk is still missing after it, reloading again would loop.
export function shouldReloadForNewBuild(lastReloadAt: number | null, now: number): boolean {
  if (lastReloadAt === null || Number.isNaN(lastReloadAt)) {
    return true
  }
  return now - lastReloadAt >= RELOAD_GUARD_MS
}

// How browsers word a failed dynamic import (Chrome, Safari, Firefox) and Vite a missing CSS.
const CHUNK_ERRORS = [
  'Failed to fetch dynamically imported module',
  'Importing a module script failed',
  'error loading dynamically imported module',
  'Unable to preload CSS',
]

// React.lazy rethrows the failed import during render, where the route error page catches it.
export function isChunkLoadError(error: unknown): boolean {
  return error instanceof Error && CHUNK_ERRORS.some((message) => error.message.includes(message))
}

function readLastReload(): number | null {
  try {
    const value = sessionStorage.getItem(STORAGE_KEY)
    return value === null ? null : Number(value)
  } catch {
    return null
  }
}

// False when the page has just reloaded for this and the file is still missing.
export function canReloadForNewBuild(): boolean {
  return shouldReloadForNewBuild(readLastReload(), Date.now())
}

// Reloads once per guard window; returns false instead of looping.
export function reloadForNewBuild(): boolean {
  const now = Date.now()
  if (!shouldReloadForNewBuild(readLastReload(), now)) {
    return false
  }
  try {
    sessionStorage.setItem(STORAGE_KEY, String(now))
  } catch {
    // Without storage the guard is off, but the reload itself still helps.
  }
  window.location.reload()
  return true
}

export function reloadOnStaleBuild(): void {
  window.addEventListener('vite:preloadError', (event) => {
    if (reloadForNewBuild()) {
      // Handled here: the failed import is not rethrown while the page reloads.
      event.preventDefault()
    }
  })
}
