import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from '@/shared/api'
import {
  readCachedTheme,
  themeFromResponse,
  type BrandTheme,
  type ThemeResponse,
} from '../model/theme'

export const themeKeys = { current: ['theme'] as const }

// The logo link is signed for an hour; re-read well before it expires.
const REFRESH_MS = 30 * 60 * 1000

export async function fetchTheme(): Promise<ThemeResponse | null> {
  const result = await api.GET('/api/v1/theme')
  if (result.response.status === 404) {
    return null
  }
  return unwrap(Promise.resolve(result))
}

export function useTheme(enabled = true) {
  return useQuery({
    queryKey: themeKeys.current,
    queryFn: fetchTheme,
    enabled,
    staleTime: REFRESH_MS,
    refetchInterval: REFRESH_MS,
  })
}

// The theme to show right now: the loaded one, or the last known one while loading.
// enabled is off before sign-in: GET /theme needs a token, and only the cache is available.
export function useBrandTheme(enabled = true): BrandTheme {
  const theme = useTheme(enabled)
  return theme.isSuccess ? themeFromResponse(theme.data) : readCachedTheme()
}

export function useBrandColor(): string {
  return useBrandTheme().primaryColor
}
