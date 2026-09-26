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

export function applyTheme(theme: BrandTheme): void {
  document.documentElement.style.setProperty('--brand', theme.primaryColor)
  document.title = `${theme.companyName} — панель`
  // The login screen cannot fetch the theme, so it reads this. The logo link expires in an hour.
  localStorage.setItem(
    CACHE_KEY,
    JSON.stringify({ companyName: theme.companyName, primaryColor: theme.primaryColor }),
  )
}

export function readCachedTheme(): BrandTheme {
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
      return { companyName: cached.companyName, primaryColor: cached.primaryColor, logoUrl: null }
    }
  } catch {
    // A broken cache is the same as no cache.
  }
  return DEFAULT_THEME
}
