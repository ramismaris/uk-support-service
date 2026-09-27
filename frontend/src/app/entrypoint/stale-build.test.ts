import { describe, expect, it } from 'vitest'
import { isChunkLoadError, RELOAD_GUARD_MS, shouldReloadForNewBuild } from './stale-build'

describe('shouldReloadForNewBuild', () => {
  it('reloads when there was no reload before', () => {
    expect(shouldReloadForNewBuild(null, 1_000_000)).toBe(true)
  })

  it('does not reload again right after a reload, so a missing file cannot loop the page', () => {
    expect(shouldReloadForNewBuild(1_000_000, 1_000_000 + RELOAD_GUARD_MS - 1)).toBe(false)
  })

  it('reloads again once the guard has passed (the next deploy)', () => {
    expect(shouldReloadForNewBuild(1_000_000, 1_000_000 + RELOAD_GUARD_MS)).toBe(true)
  })

  it('treats a broken stored value as no reload', () => {
    expect(shouldReloadForNewBuild(Number.NaN, 1_000_000)).toBe(true)
  })
})

describe('isChunkLoadError', () => {
  it.each([
    'Failed to fetch dynamically imported module: https://uk.example/assets/RichTextField-1.js',
    'Importing a module script failed.',
    'error loading dynamically imported module: https://uk.example/assets/a.js',
    'Unable to preload CSS for /assets/a.css',
  ])('recognises a chunk missing after a deploy: %s', (message) => {
    expect(isChunkLoadError(new TypeError(message))).toBe(true)
  })

  it('does not take other errors for it', () => {
    expect(
      isChunkLoadError(new TypeError("Cannot read properties of undefined (reading 'id')")),
    ).toBe(false)
    expect(isChunkLoadError('Failed to fetch dynamically imported module')).toBe(false)
  })
})
