import { MaxUI } from '@maxhub/max-ui'
import { useLayoutEffect, type ReactNode } from 'react'
import { useColorScheme } from '@/shared/lib/color-scheme'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const colorScheme = useColorScheme()

  // Same scheme for Max UI and for Tailwind's dark: variant.
  useLayoutEffect(() => {
    document.documentElement.dataset.colorScheme = colorScheme
  }, [colorScheme])

  return <MaxUI colorScheme={colorScheme}>{children}</MaxUI>
}
