import type { components } from '@/shared/api'
import { parseHexColor } from '@/shared/lib/color'

export type ThemeResponse = components['schemas']['ThemeContentResponse']

export interface BrandTheme {
  companyName: string
  primaryColor: string
  logoUrl: string | null
}

export const DEFAULT_THEME: BrandTheme = {
  companyName: 'Панель УК',
  primaryColor: '#007aff',
  logoUrl: null,
}

const CACHE_KEY = 'uk-theme'

// The logo link is signed for an hour: a cached one is used only while it surely still works.
export const LOGO_FRESH_MS = 50 * 60 * 1000

// null — the admin has not set the theme up yet (GET /theme answers 404).
export function themeFromResponse(response: ThemeResponse | null): BrandTheme {
  if (!response) {
    return DEFAULT_THEME
  }
  return {
    companyName: response.company_name,
    primaryColor: response.primary_color,
    logoUrl: response.logo_url,
  }
}

export function paintTheme(theme: BrandTheme): void {
  document.documentElement.style.setProperty('--brand', theme.primaryColor)
  document.title = `${theme.companyName} — панель`
}

// The login screen and the first frame cannot fetch the theme, so they read the cache.
export function applyTheme(theme: BrandTheme, now = Date.now()): void {
  paintTheme(theme)
  try {
    localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({
        companyName: theme.companyName,
        primaryColor: theme.primaryColor,
        logoUrl: theme.logoUrl,
        savedAt: now,
      }),
    )
  } catch {
    // Storage can be disabled (some WebViews); the theme still applies, only the cache is lost.
  }
}

export function readCachedTheme(now = Date.now()): BrandTheme {
  try {
    const cached: unknown = JSON.parse(localStorage.getItem(CACHE_KEY) ?? 'null')
    if (
      cached &&
      typeof cached === 'object' &&
      'companyName' in cached &&
      'primaryColor' in cached &&
      typeof cached.companyName === 'string' &&
      typeof cached.primaryColor === 'string' &&
      parseHexColor(cached.primaryColor)
    ) {
      const fresh =
        'savedAt' in cached &&
        typeof cached.savedAt === 'number' &&
        now - cached.savedAt <= LOGO_FRESH_MS
      const logoUrl =
        fresh && 'logoUrl' in cached && typeof cached.logoUrl === 'string' ? cached.logoUrl : null
      return { companyName: cached.companyName, primaryColor: cached.primaryColor, logoUrl }
    }
  } catch {
    // A broken cache is the same as no cache.
  }
  return DEFAULT_THEME
}
