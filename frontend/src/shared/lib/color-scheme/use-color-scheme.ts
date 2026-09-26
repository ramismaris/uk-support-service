import { useSyncExternalStore } from 'react'

export type ColorScheme = 'light' | 'dark'

const DARK_QUERY = '(prefers-color-scheme: dark)'

function subscribe(onChange: () => void): () => void {
  const media = window.matchMedia(DARK_QUERY)
  media.addEventListener('change', onChange)
  return () => media.removeEventListener('change', onChange)
}

function getSnapshot(): ColorScheme {
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light'
}

export function useColorScheme(): ColorScheme {
  return useSyncExternalStore(subscribe, getSnapshot)
}
