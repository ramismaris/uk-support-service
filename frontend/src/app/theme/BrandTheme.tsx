import { useEffect } from 'react'
import { useSessionStore } from '@/entities/session'
import { applyTheme, themeFromResponse, useTheme } from '@/entities/theme'

// Applies the company theme once signed in (GET /theme needs a token).
export function BrandTheme() {
  const token = useSessionStore((state) => state.token)
  const theme = useTheme(token !== null)

  useEffect(() => {
    if (theme.isSuccess) {
      applyTheme(themeFromResponse(theme.data))
    }
  }, [theme.isSuccess, theme.data])

  return null
}
