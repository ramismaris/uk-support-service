import { useSessionStore } from '@/entities/session'
import { useBrandTheme } from '@/entities/theme'
import { SplashScreen } from '@/shared/ui/splash-screen'
import { BrandLogo } from './BrandLogo'

// The screen shown while the session loads: the company's logo and name from the cache.
export function BrandSplash() {
  const token = useSessionStore((state) => state.token)
  const theme = useBrandTheme(token !== null)
  return <SplashScreen name={theme.companyName} mark={<BrandLogo theme={theme} size="xl" />} />
}
