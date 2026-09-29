import type { ImageValue } from '@/features/upload-image'

interface ThemeDraft {
  companyName: string
  primaryColor: string
  logo: ImageValue | null
}

// The logo stays out of the stored draft: its signed link does not last.
export function storableTheme({ companyName, primaryColor }: ThemeDraft) {
  return { companyName, primaryColor }
}

export function restoreTheme(saved: ThemeDraft, raw: unknown): ThemeDraft | null {
  if (typeof raw !== 'object' || raw === null) {
    return null
  }
  const { companyName, primaryColor } = raw as Record<string, unknown>
  if (typeof companyName !== 'string' || typeof primaryColor !== 'string') {
    return null
  }
  return { ...saved, companyName, primaryColor }
}
