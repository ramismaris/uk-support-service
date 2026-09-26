import { useCallback, useSyncExternalStore } from 'react'

export const breakpoints = {
  lg: '(min-width: 1024px)',
  xl: '(min-width: 1280px)',
} as const

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const media = window.matchMedia(query)
      media.addEventListener('change', onChange)
      return () => media.removeEventListener('change', onChange)
    },
    [query],
  )
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches)
}
