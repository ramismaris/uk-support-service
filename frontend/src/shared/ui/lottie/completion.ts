// The player's "complete" event never fires when motion is reduced or the player fails to load,
// so completion also has a timed fallback.
export function completionFallbackDelay(reduced: boolean, fallbackMs: number): number {
  return reduced ? 0 : fallbackMs
}

export function once(handler: () => void): () => void {
  let called = false
  return () => {
    if (!called) {
      called = true
      handler()
    }
  }
}
