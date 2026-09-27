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

function readLastReload(): number | null {
  try {
    const value = sessionStorage.getItem(STORAGE_KEY)
    return value === null ? null : Number(value)
  } catch {
    return null
  }
}

export function reloadOnStaleBuild(): void {
  window.addEventListener('vite:preloadError', (event) => {
    const now = Date.now()
    if (!shouldReloadForNewBuild(readLastReload(), now)) {
      return
    }
    // Handled here: the failed import is not rethrown while the page reloads.
    event.preventDefault()
    try {
      sessionStorage.setItem(STORAGE_KEY, String(now))
    } catch {
      // Without storage the guard is off, but the reload itself still helps.
    }
    window.location.reload()
  })
}
